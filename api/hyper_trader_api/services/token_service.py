"""
JWT token service for access token management.

Handles creation and verification of JWT tokens for authentication.
"""

from datetime import UTC, datetime, timedelta

import jwt

from hyper_trader_api.models.user import User


class TokenService:
    """
    Service for JWT token creation and verification.

    Uses PyJWT for token operations with HS256 algorithm.
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize token service.

        Args:
            secret_key: Secret key for signing JWT tokens
            algorithm: JWT signing algorithm (default: HS256)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_access_token(
        self,
        user: User,
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        Create a JWT access token for a user.

        Args:
            user: User object to create token for
            expires_delta: Optional custom expiration time (default: 24 hours)

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=24)

        now = datetime.now(UTC)
        expire = now + expires_delta

        payload = {
            "sub": user.id,
            "username": user.username,
            "is_admin": user.is_admin,
            "exp": expire,
            "iat": now,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_access_token(self, token: str) -> dict | None:
        """
        Verify and decode a JWT access token.

        Args:
            token: JWT token string to verify

        Returns:
            Decoded token payload dict if valid, None otherwise
        """
        if not token:
            return None

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
            )
            return payload
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Invalid token (wrong signature, malformed, etc.)
            return None
        except Exception:
            # Other errors (malformed token, etc.)
            return None
