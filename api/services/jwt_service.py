"""
JWT authentication service for HyperTrader API.

Handles JWT token generation, validation, and refresh token management.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from api.config import get_settings
from api.models import User, RefreshToken
from api.utils.crypto import hash_token


class JWTService:
    """
    JWT authentication service.

    Handles:
    - Access token generation and validation
    - Refresh token generation, storage, and rotation
    - Token revocation
    """

    @staticmethod
    def create_access_token(user_id: uuid.UUID, email: str) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User's UUID
            email: User's email

        Returns:
            str: JWT access token
        """
        settings = get_settings()
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode = {
            "sub": str(user_id),
            "email": email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        return encoded_jwt

    @staticmethod
    def create_refresh_token(db: Session, user_id: uuid.UUID) -> str:
        """
        Create a refresh token and store it in the database.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            str: JWT refresh token
        """
        settings = get_settings()
        expires_delta = timedelta(days=settings.jwt_refresh_token_expire_days)
        expire = datetime.now(timezone.utc) + expires_delta

        # Generate unique token ID
        token_id = str(uuid.uuid4())

        to_encode = {
            "sub": str(user_id),
            "jti": token_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Store token hash in database for revocation
        token_hash = hash_token(encoded_jwt)
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expire,
        )

        db.add(refresh_token)
        db.commit()

        return encoded_jwt

    @staticmethod
    def verify_access_token(token: str) -> Optional[dict]:
        """
        Verify and decode an access token.

        Args:
            token: JWT access token

        Returns:
            dict: Token payload if valid, None if invalid
        """
        settings = get_settings()

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )

            # Verify token type
            if payload.get("type") != "access":
                return None

            return payload

        except JWTError:
            return None

    @staticmethod
    def verify_refresh_token(db: Session, token: str) -> Optional[dict]:
        """
        Verify a refresh token and check if it's been revoked.

        Args:
            db: Database session
            token: JWT refresh token

        Returns:
            dict: Token payload if valid and not revoked, None otherwise
        """
        settings = get_settings()

        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )

            # Verify token type
            if payload.get("type") != "refresh":
                return None

            # Check if token has been revoked
            token_hash = hash_token(token)
            db_token = (
                db.query(RefreshToken)
                .filter(
                    RefreshToken.token_hash == token_hash,
                    RefreshToken.revoked == False,
                )
                .first()
            )

            if not db_token:
                return None

            # Check if token has expired (double-check)
            if db_token.expires_at < datetime.now(timezone.utc):
                return None

            return payload

        except JWTError:
            return None

    @staticmethod
    def revoke_refresh_token(db: Session, token: str) -> bool:
        """
        Revoke a refresh token.

        Args:
            db: Database session
            token: JWT refresh token to revoke

        Returns:
            bool: True if token was revoked, False if not found
        """
        token_hash = hash_token(token)
        db_token = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()

        if not db_token:
            return False

        db_token.revoked = True
        db.commit()

        return True

    @staticmethod
    def revoke_all_user_tokens(db: Session, user_id: uuid.UUID) -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            int: Number of tokens revoked
        """
        count = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            )
            .update({"revoked": True})
        )

        db.commit()

        return count

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """
        Delete expired refresh tokens from the database.

        Args:
            db: Database session

        Returns:
            int: Number of tokens deleted
        """
        now = datetime.now(timezone.utc)
        count = db.query(RefreshToken).filter(RefreshToken.expires_at < now).delete()

        db.commit()

        return count
