"""
User model for HyperTrader API.

Represents user accounts authenticated via Privy wallet authentication.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from hyper_trader_api.database import Base

if TYPE_CHECKING:
    from hyper_trader_api.models.trader import Trader


class User(Base):
    """
    User account model with Privy authentication.

    Attributes:
        id: Unique identifier (UUID string)
        privy_user_id: Privy user DID (unique, indexed)
        wallet_address: Ethereum wallet address (unique, indexed)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        traders: List of traders owned by this user
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    privy_user_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    wallet_address: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
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

    def __repr__(self) -> str:
        return f"<User(id={self.id}, privy_user_id={self.privy_user_id}, wallet={self.wallet_address})>"
