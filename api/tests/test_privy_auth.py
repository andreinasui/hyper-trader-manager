"""
Tests for Privy authentication.

Tests the Privy JWT verification and user creation flow.
Note: PrivyService tests are skipped as Privy auth has been replaced
with local username/password auth in the v1 release.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from hyper_trader_api.services.privy_service import PrivyError, PrivyService


@pytest.mark.skip(reason="Privy auth replaced by local auth in v1")
class TestPrivyService:
    """Test Privy service functionality."""

    @pytest.fixture
    def privy_service(self):
        """Create a Privy service instance for testing."""
        with patch("hyper_trader_api.services.privy_service.get_settings") as mock_settings:
            mock_settings.return_value.privy_app_id = "test-app-id"
            mock_settings.return_value.privy_app_secret = "test-secret"
            mock_settings.return_value.privy_verification_key = "test-key"
            service = PrivyService()
            yield service

    def test_verify_access_token_invalid_token(self, privy_service):
        """Test that invalid tokens raise PrivyError."""
        with pytest.raises(PrivyError):
            privy_service.verify_access_token("invalid_token")

    @pytest.mark.asyncio
    async def test_get_user_info_api_error(self, privy_service):
        """Test that API errors are handled properly."""
        privy_service.client = AsyncMock()
        privy_service.client.get = AsyncMock(side_effect=Exception("API Error"))

        with pytest.raises(PrivyError):
            await privy_service.get_user_info("did:privy:test123")

    @pytest.mark.asyncio
    async def test_get_wallet_address_no_wallet(self, privy_service):
        """Test that missing wallet raises PrivyError."""
        privy_service.get_user_info = AsyncMock(return_value={"linked_accounts": []})

        with pytest.raises(PrivyError, match="No wallet found"):
            await privy_service.get_wallet_address("did:privy:test123")

    @pytest.mark.asyncio
    async def test_get_wallet_address_success(self, privy_service):
        """Test successful wallet address extraction."""
        privy_service.get_user_info = AsyncMock(
            return_value={
                "linked_accounts": [
                    {"type": "wallet", "address": "0x1234567890abcdef1234567890abcdef12345678"}
                ]
            }
        )

        wallet = await privy_service.get_wallet_address("did:privy:test123")
        assert wallet == "0x1234567890abcdef1234567890abcdef12345678"


@pytest.mark.skip(reason="Auth middleware tests moved to test_session_auth.py")
class TestAuthMiddleware:
    """Test authentication middleware."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test that missing Authorization header returns 401."""
        from fastapi import Request

        from hyper_trader_api.middleware.session_auth import get_current_user

        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, db)

        assert exc_info.value.status_code == 401
        assert "Missing or invalid authorization header" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_authorization_format(self):
        """Test that invalid Authorization format returns 401."""
        from fastapi import Request

        from hyper_trader_api.middleware.session_auth import get_current_user

        request = MagicMock(spec=Request)
        request.headers.get.return_value = "InvalidFormat token"
        db = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, db)

        assert exc_info.value.status_code == 401
