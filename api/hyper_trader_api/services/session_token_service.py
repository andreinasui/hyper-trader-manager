"""
Session token service for opaque token-based authentication.

Provides creation, verification, and revocation of session tokens
as a replacement for JWT-based authentication.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from hyper_trader_api.models.session_token import SessionToken
from hyper_trader_api.models.user import User

_TOKEN_PREFIX = "htk_"


def _hash_token(token: str) -> str:
    """Return the SHA256 hex-digest of *token*."""
    return hashlib.sha256(token.encode()).hexdigest()


class SessionTokenService:
    """
    Service for opaque session token management.

    Tokens are prefixed with ``htk_`` and backed by a random 32-byte
    URL-safe secret.  Only the SHA256 hash of each token is persisted;
    the raw token is returned once to the caller and never stored.
    """

    def __init__(self, db: Session) -> None:
        """
        Initialise the service.

        Args:
            db: SQLAlchemy database session.
        """
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session(self, user: User, expires_days: int = 30) -> str:
        """
        Generate a new session token for *user* and persist its hash.

        Args:
            user: The authenticated user to create a session for.
            expires_days: Number of days until the token expires (default 30).

        Returns:
            The raw opaque token string (``htk_…``).  Store this value
            securely — it will not be retrievable again.
        """
        raw_token = _TOKEN_PREFIX + secrets.token_urlsafe(32)
        token_hash = _hash_token(raw_token)

        expires_at = datetime.now(UTC) + timedelta(days=expires_days)

        session = SessionToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )

        self.db.add(session)
        self.db.commit()

        return raw_token

    def verify_session(self, token: str) -> str | None:
        """
        Verify *token* and return the associated ``user_id`` if valid.

        A token is considered valid when:
        - Its hash exists in the database.
        - ``is_revoked`` is ``False``.
        - ``expires_at`` is in the future.

        Args:
            token: Raw opaque token supplied by the client.

        Returns:
            ``user_id`` string if the token is valid, ``None`` otherwise.
        """
        if not token:
            return None

        token_hash = _hash_token(token)
        now = datetime.now(UTC)

        session = (
            self.db.query(SessionToken)
            .filter(SessionToken.token_hash == token_hash)
            .first()
        )

        if session is None:
            return None

        if session.is_revoked:
            return None

        if session.expires_at <= now:
            return None

        return session.user_id

    def revoke_session(self, token: str) -> bool:
        """
        Revoke the session identified by *token*.

        Args:
            token: Raw opaque token to revoke.

        Returns:
            ``True`` if the session was found and revoked,
            ``False`` if the token was unknown or empty.
        """
        if not token:
            return False

        token_hash = _hash_token(token)

        session = (
            self.db.query(SessionToken)
            .filter(SessionToken.token_hash == token_hash)
            .first()
        )

        if session is None:
            return False

        session.is_revoked = True
        self.db.commit()

        return True
