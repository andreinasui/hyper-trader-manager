"""
User model for HyperTrader API.

Represents user accounts with API key authentication and plan tiers.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.database import Base

if TYPE_CHECKING:
    from api.models.trader import Trader
    from api.models.refresh_token import RefreshToken


class User(Base):
    """
    User account model.

    Attributes:
        id: Unique identifier (UUID)
        email: User's email address (unique)
        api_key_hash: Hashed API key for authentication (optional for password-only users)
        password_hash: Hashed password for JWT authentication (optional for API-key-only users)
        is_admin: Whether the user has admin privileges
        plan_tier: Subscription tier (free, pro, enterprise)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        traders: List of traders owned by this user
        refresh_tokens: List of active refresh tokens
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    api_key_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    plan_tier: Mapped[str] = mapped_column(
        String(50),
        default="free",
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
    traders: Mapped[List["Trader"]] = relationship(
        "Trader",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, plan={self.plan_tier}, admin={self.is_admin})>"

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, plan={self.plan_tier})>"
