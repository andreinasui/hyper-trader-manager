"""SSL configuration model."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from hyper_trader_api.database import Base


class SSLConfig(Base):
    """Stores SSL setup configuration. Singleton table (only one row).

    Attributes:
        id: Primary key, always 1 (singleton pattern)
        mode: SSL mode - "domain" (Let's Encrypt)
        domain: The domain name if using Let's Encrypt
        email: Email address for Let's Encrypt certificate notifications
        configured_at: When SSL was first configured
        created_at: Row creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "ssl_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    mode: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "domain" | null
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    configured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<SSLConfig(id={self.id}, mode={self.mode}, domain={self.domain})>"
