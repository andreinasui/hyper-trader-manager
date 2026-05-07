"""
TraderLogArchive response schema.

NOTE: file_path is intentionally excluded — it is a server-side implementation
detail and must never be exposed to API consumers.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_validator


class TraderLogArchiveResponse(BaseModel):
    """Public response schema for a trader log archive entry.

    The ``file_path`` field from the database model is deliberately omitted:
    callers receive only the metadata they need to identify and download an
    archive; the physical path on disk is a server-only concern.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    trader_id: str
    run_started_at: datetime
    run_ended_at: datetime
    file_size_bytes: int
    created_at: datetime

    @field_validator("run_started_at", "run_ended_at", "created_at", mode="before")
    @classmethod
    def ensure_utc(cls, v: object) -> object:
        """Attach UTC timezone to naive datetimes returned by SQLite.

        SQLite does not store timezone information; SQLAlchemy returns naive
        datetime objects even when the column is declared with timezone=True.
        Without this validator, Pydantic serialises them without a timezone
        offset, and browsers interpret the bare ISO string as local time rather
        than UTC, producing incorrect display values.
        """
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v
