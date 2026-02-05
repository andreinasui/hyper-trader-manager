"""
Privy authentication service for HyperTrader API.

Handles JWT verification via JWKS and user info retrieval from Privy.
"""

import logging
from typing import Any

import httpx
import jwt
from jwt import PyJWKClient

from hyper_trader_api.config import get_settings

logger = logging.getLogger(__name__)


class PrivyError(Exception):
    """Base exception for Privy-related errors."""

    pass


class PrivyService:
    """
    Service for interacting with Privy authentication.

    Uses Privy's JWKS endpoint for automatic key rotation support.
    """

    PRIVY_API_BASE = "https://auth.privy.io/api/v1"

    def __init__(self) -> None:
        """Initialize Privy service with JWKS client and HTTP client."""
        self.settings = get_settings()

        # JWKS client for token verification (with caching)
        self.jwks_client = PyJWKClient(
            self.settings.privy_jwks_endpoint,
            cache_keys=True,
            lifespan=self.settings.privy_jwks_cache_ttl,
        )

        # HTTP client for Privy API calls
        self.client = httpx.AsyncClient(
            base_url=self.PRIVY_API_BASE,
            headers={
                "privy-app-id": self.settings.privy_app_id,
                "Authorization": f"Bearer {self.settings.privy_app_secret}",
            },
            timeout=self.settings.http_timeout,
        )

    def verify_access_token(self, access_token: str) -> dict[str, Any]:
        """
        Verify Privy JWT access token using JWKS.

        Args:
            access_token: JWT token from Privy

        Returns:
            Decoded JWT payload containing user info

        Raises:
            PrivyError: If token is invalid or verification fails
        """
        try:
            # Get signing key from JWKS (cached)
            signing_key = self.jwks_client.get_signing_key_from_jwt(access_token)

            # Verify and decode
            payload = jwt.decode(
                access_token,
                signing_key.key,
                algorithms=["ES256"],
                audience=self.settings.privy_app_id,
            )

            # Extract subject (Privy user DID)
            privy_user_id = payload.get("sub")
            if not privy_user_id:
                raise PrivyError("Token missing subject claim")

            logger.debug(f"Token verified for Privy user: {privy_user_id}")
            return payload

        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT verification failed: {e}")
            raise PrivyError(f"Invalid token: {str(e)}") from e

    async def get_user_info(self, privy_user_id: str) -> dict[str, Any]:
        """
        Fetch user information from Privy API.

        Args:
            privy_user_id: Privy user DID (format: did:privy:xxx)

        Returns:
            User data from Privy API

        Raises:
            PrivyError: If API request fails
        """
        try:
            response = await self.client.get(f"/users/{privy_user_id}")
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"Privy API error: {e.response.status_code} - {e.response.text}")
            raise PrivyError(f"Failed to fetch user info: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Privy API request failed: {e}")
            raise PrivyError(f"Failed to connect to Privy API: {str(e)}") from e

    async def get_wallet_address(self, privy_user_id: str) -> str:
        """
        Extract wallet address from user's linked accounts.

        Args:
            privy_user_id: Privy user DID

        Returns:
            Ethereum wallet address

        Raises:
            PrivyError: If no wallet found or API request fails
        """
        user_info = await self.get_user_info(privy_user_id)

        # Extract wallet from linked accounts
        linked_accounts = user_info.get("linked_accounts", [])

        for account in linked_accounts:
            if account.get("type") == "wallet":
                wallet_address = account.get("address")
                if wallet_address:
                    logger.debug(f"Found wallet for {privy_user_id}: {wallet_address}")
                    return wallet_address

        raise PrivyError(f"No wallet found for user {privy_user_id}")

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
_privy_service: PrivyService | None = None


def get_privy_service() -> PrivyService:
    """
    Get singleton PrivyService instance.

    Returns:
        PrivyService: Shared service instance
    """
    global _privy_service
    if _privy_service is None:
        _privy_service = PrivyService()
    return _privy_service
