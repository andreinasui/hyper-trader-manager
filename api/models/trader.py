"""
Trader-related models for HyperTrader API.

Contains models for traders, their configurations, secrets, deployments,
and usage metrics.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from api.database import Base

if TYPE_CHECKING:
    from api.models.user import User


class Trader(Base):
    """
    Trader instance model.

    Represents a trading bot deployment in Kubernetes.
    Each trader has a unique wallet address and K8s name.

    Attributes:
        id: Unique identifier (UUID)
        user_id: Foreign key to owning user
        wallet_address: Ethereum wallet address (unique)
        k8s_name: Kubernetes resource name (unique)
        status: Current status (pending, running, stopped, failed)
        image_tag: Docker image tag for deployment
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "traders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wallet_address: Mapped[str] = mapped_column(
        String(42),
        unique=True,
        nullable=False,
    )
    k8s_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        index=True,
    )
    image_tag: Mapped[str] = mapped_column(
        String(100),
        default="latest",
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
    user: Mapped["User"] = relationship(
        "User",
        back_populates="traders",
    )
    configs: Mapped[List["TraderConfig"]] = relationship(
        "TraderConfig",
        back_populates="trader",
        cascade="all, delete-orphan",
        order_by="TraderConfig.version.desc()",
    )
    secret: Mapped[Optional["TraderSecret"]] = relationship(
        "TraderSecret",
        back_populates="trader",
        uselist=False,
        cascade="all, delete-orphan",
    )
    deployments: Mapped[List["Deployment"]] = relationship(
        "Deployment",
        back_populates="trader",
        cascade="all, delete-orphan",
        order_by="Deployment.deployed_at.desc()",
    )
    usage_metrics: Mapped[List["UsageMetric"]] = relationship(
        "UsageMetric",
        back_populates="trader",
        cascade="all, delete-orphan",
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

    Attributes:
        id: Unique identifier (UUID)
        trader_id: Foreign key to trader
        config_json: Configuration as JSONB
        version: Configuration version number
        created_at: Creation timestamp
    """

    __tablename__ = "trader_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    trader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traders.id", ondelete="CASCADE"),
        nullable=False,
    )
    config_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
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
    __table_args__ = ({"extend_existing": True},)

    def __repr__(self) -> str:
        return f"<TraderConfig(trader_id={self.trader_id}, version={self.version})>"


class TraderSecret(Base):
    """
    Encrypted trader secrets.

    Stores encrypted private keys with reference to encryption key.
    One-to-one relationship with Trader.

    Attributes:
        id: Unique identifier (UUID)
        trader_id: Foreign key to trader (unique)
        encrypted_private_key: Encrypted private key
        encryption_key_id: Reference to encryption key used
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "trader_secrets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    trader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traders.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    encrypted_private_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    encryption_key_id: Mapped[Optional[str]] = mapped_column(
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

    # Relationships
    trader: Mapped["Trader"] = relationship(
        "Trader",
        back_populates="secret",
    )

    def __repr__(self) -> str:
        return f"<TraderSecret(trader_id={self.trader_id})>"


class Deployment(Base):
    """
    Deployment history record.

    Tracks all deployment attempts for audit and rollback.

    Attributes:
        id: Unique identifier (UUID)
        trader_id: Foreign key to trader
        image_tag: Docker image tag deployed
        status: Deployment status
        k8s_metadata: Additional Kubernetes metadata (JSONB)
        deployed_at: Deployment start timestamp
        completed_at: Deployment completion timestamp
    """

    __tablename__ = "deployments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    trader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    image_tag: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    k8s_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    trader: Mapped["Trader"] = relationship(
        "Trader",
        back_populates="deployments",
    )

    def __repr__(self) -> str:
        return f"<Deployment(trader_id={self.trader_id}, status={self.status})>"


class UsageMetric(Base):
    """
    Usage metrics for billing and analytics.

    Time-series data tracking resource usage per trader.

    Attributes:
        id: Unique identifier (UUID)
        trader_id: Foreign key to trader
        timestamp: Metric timestamp
        metric_type: Type of metric (cpu_hours, memory_gb_hours, etc.)
        value: Metric value
        extra_data: Additional metadata (JSONB)
    """

    __tablename__ = "usage_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    trader_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("traders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    metric_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric,
        nullable=True,
    )
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Relationships
    trader: Mapped["Trader"] = relationship(
        "Trader",
        back_populates="usage_metrics",
    )

    def __repr__(self) -> str:
        return f"<UsageMetric(trader_id={self.trader_id}, type={self.metric_type})>"
