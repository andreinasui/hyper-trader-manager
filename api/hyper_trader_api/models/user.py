"""
User model for HyperTrader API.

Represents user accounts with local username/password authentication.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from hyper_trader_api.database import Base

if TYPE_CHECKING:
    from hyper_trader_api.models.session_token import SessionToken
    from hyper_trader_api.models.trader import Trader


class User(Base):
    """
    User account model with local authentication.

    Uses username/password instead of Privy.

    Attributes:
        id: Unique identifier (UUID string)
        username: Username for login (unique, indexed)
        password_hash: Bcrypt password hash
        is_admin: Whether user has admin privileges
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        traders: List of traders owned by this user
        session_tokens: List of active session tokens
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    traders: Mapped[list["Trader"]] = relationship(
        "Trader",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    session_tokens: Mapped[list["SessionToken"]] = relationship(
        "SessionToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, is_admin={self.is_admin})>"
