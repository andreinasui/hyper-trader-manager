"""TraderLogArchive model — one row per archived trader run."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from hyper_trader_api.database import Base

if TYPE_CHECKING:
    from hyper_trader_api.models.trader import Trader


class TraderLogArchive(Base):
    """A gzipped log archive captured at the end of a single trader run."""

    __tablename__ = "trader_log_archives"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    trader_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("traders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    run_ended_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(
        String(1024),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    trader: Mapped[Trader] = relationship(
        "Trader",
        back_populates="log_archives",
    )

    def __repr__(self) -> str:
        return (
            f"<TraderLogArchive(id={self.id}, trader_id={self.trader_id}, "
            f"run_started_at={self.run_started_at})>"
        )
