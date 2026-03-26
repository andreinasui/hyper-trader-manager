"""
Session token model for JWT token revocation.

Tracks active session tokens to support logout and token revocation.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from hyper_trader_api.database import Base

if TYPE_CHECKING:
    from hyper_trader_api.models.user import User


class SessionToken(Base):
    """
    Session token for JWT revocation tracking.

    Stores hashed tokens to enable logout and token invalidation
    for self-hosted authentication.

    Attributes:
        id: Unique identifier (UUID string)
        user_id: Foreign key to user
        token_hash: Hash of the JWT token (for lookup on verification)
        expires_at: Token expiration timestamp
        is_revoked: Whether token has been manually revoked
        created_at: Creation timestamp
    """

    __tablename__ = "session_tokens"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="session_tokens",
    )

    def __repr__(self) -> str:
        return f"<SessionToken(user_id={self.user_id}, revoked={self.is_revoked})>"
