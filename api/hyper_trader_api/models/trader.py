"""
Trader-related models for HyperTrader API.

Contains models for traders and their configurations
with SQLite compatibility.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.types import JSON

from hyper_trader_api.database import Base

if TYPE_CHECKING:
    from hyper_trader_api.models.user import User


class Trader(Base):
    """
    Trader instance model.

    Represents a trading bot deployment in Docker container.
    Each trader has a unique wallet address and runtime name.

    Attributes:
        id: Unique identifier (UUID string for SQLite compatibility)
        user_id: Foreign key to owning user
        wallet_address: Ethereum wallet address (unique)
        runtime_name: Docker container name (unique)
        status: Current status (configured, starting, running, stopped, failed)
        start_attempts: Number of start attempts (for retry logic, max 3)
        last_error: Error message when status is failed
        stopped_at: Timestamp when user stopped the trader
        image_tag: Docker image tag for deployment
        name: Optional user-friendly display name (unique per user, max 50 chars)
        description: Optional notes about the trader (max 255 chars)
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "traders"

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
    wallet_address: Mapped[str] = mapped_column(
        String(42),
        unique=True,
        nullable=False,
    )
    runtime_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="configured",
        index=True,
    )
    start_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    last_error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )
    stopped_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    image_tag: Mapped[str] = mapped_column(
        String(100),
        default="latest",
    )
    name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
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

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_trader_user_name"),)

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="traders",
    )
    configs: Mapped[list["TraderConfig"]] = relationship(
        "TraderConfig",
        back_populates="trader",
        cascade="all, delete-orphan",
        order_by="TraderConfig.version.desc()",
    )

    @property
    def latest_config(self) -> Optional["TraderConfig"]:
        """Get the most recent configuration version."""
        return self.configs[0] if self.configs else None

    def __repr__(self) -> str:
        return f"<Trader(id={self.id}, address={self.wallet_address}, status={self.status})>"


class TraderConfig(Base):
    """
    Versioned trader configuration.

    Stores JSON configuration with version history for audit and rollback.
    Uses SQLite-compatible JSON type instead of PostgreSQL JSONB.

    Attributes:
        id: Unique identifier (UUID string for SQLite compatibility)
        trader_id: Foreign key to trader
        config_json: Configuration as JSON
        version: Configuration version number
        created_at: Creation timestamp
    """

    __tablename__ = "trader_configs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    trader_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("traders.id", ondelete="CASCADE"),
        nullable=False,
    )
    config_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # Relationships
    trader: Mapped["Trader"] = relationship(
        "Trader",
        back_populates="configs",
    )

    # Unique constraint on (trader_id, version)
    __table_args__ = (UniqueConstraint("trader_id", "version", name="uq_trader_config_version"),)

    def __repr__(self) -> str:
        return f"<TraderConfig(trader_id={self.trader_id}, version={self.version})>"
