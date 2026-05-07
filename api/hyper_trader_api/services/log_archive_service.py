"""LogArchiveService — captures Docker service logs to gzipped files on stop.

Storage layout: <LOG_ARCHIVE_DIR>/<trader_id>/<run_started_at>.tar.gz

The archive directory is a fixed module-level constant pointing at the
container-mounted volume. It is intentionally NOT a Settings field so it
can't be overridden via environment variables in production.
"""

from __future__ import annotations

import io
import logging
import os
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from hyper_trader_api.models import Trader, TraderLogArchive
from hyper_trader_api.runtime import TraderRuntime, get_runtime

logger = logging.getLogger(__name__)

LOG_ARCHIVE_DIR = Path("/app/data/logs")
"""Container-side path; the host mount is configured in docker-compose."""

_FILENAME_FMT = "%Y%m%dT%H%M%SZ"


class LogArchiveService:
    """Manage trader log archive files and their DB rows."""

    def __init__(
        self,
        db: Session,
        archive_dir: Path | None = None,
        runtime: TraderRuntime | None = None,
    ) -> None:
        self.db = db
        self.archive_dir = archive_dir or LOG_ARCHIVE_DIR
        self.runtime = runtime or get_runtime()

    def _trader_dir(self, trader_id: str) -> Path:
        return self.archive_dir / trader_id

    def _filename_for(self, run_started_at: datetime) -> str:
        return f"{run_started_at.astimezone(UTC).strftime(_FILENAME_FMT)}.tar.gz"

    def archive_run(self, trader: Trader) -> TraderLogArchive | None:
        """Capture full logs for the current run, pack into tar.gz, persist a DB row.

        Returns the created `TraderLogArchive` on success, or `None` if there
        were no logs to archive (e.g., service never produced output).
        Raises on I/O / DB errors — callers in `TraderService` wrap this in
        a best-effort try/except.
        """
        run_started_at = trader.last_started_at or datetime.now(UTC)
        if trader.last_started_at is None:
            logger.warning("archive_run: trader %s has no last_started_at; using now()", trader.id)

        run_ended_at = datetime.now(UTC)

        logs = self.runtime.get_logs(trader.runtime_name, all_lines=True)
        if not logs:
            logger.info("archive_run: no logs for trader %s, skipping", trader.id)
            return None

        target_dir = self._trader_dir(trader.id)
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = self._filename_for(run_started_at)
        final_path = target_dir / filename
        tmp_path = final_path.with_suffix(final_path.suffix + ".tmp")

        log_bytes = logs.encode("utf-8")
        inner_name = run_started_at.astimezone(UTC).strftime(_FILENAME_FMT) + ".log"

        try:
            with tarfile.open(tmp_path, "w:gz") as tar:
                info = tarfile.TarInfo(name=inner_name)
                info.size = len(log_bytes)
                tar.addfile(info, io.BytesIO(log_bytes))
            with open(tmp_path, "rb") as fd:
                os.fsync(fd.fileno())
            os.replace(tmp_path, final_path)
        except Exception:
            # Clean up partial tmp file on any failure
            tmp_path.unlink(missing_ok=True)
            raise

        size = final_path.stat().st_size

        archive = TraderLogArchive(
            trader_id=trader.id,
            run_started_at=run_started_at,
            run_ended_at=run_ended_at,
            file_path=str(final_path),
            file_size_bytes=size,
        )
        self.db.add(archive)
        self.db.commit()
        self.db.refresh(archive)

        logger.info(
            "archive_run: archived trader %s -> %s (%d bytes)",
            trader.id,
            final_path,
            size,
        )
        return archive

    def purge_trader(self, trader_id: str) -> None:
        """Delete the trader's archive directory. Idempotent."""
        target_dir = self._trader_dir(trader_id)
        if target_dir.exists():
            shutil.rmtree(target_dir)
            logger.info("purge_trader: removed %s", target_dir)

    def list_archives(self, trader_id: str) -> list[TraderLogArchive]:
        return (
            self.db.query(TraderLogArchive)
            .filter(TraderLogArchive.trader_id == trader_id)
            .order_by(TraderLogArchive.run_started_at.desc())
            .all()
        )

    def get_archive(self, archive_id: str) -> TraderLogArchive | None:
        return self.db.query(TraderLogArchive).filter(TraderLogArchive.id == archive_id).first()

    def archive_path(self, archive: TraderLogArchive) -> Path:
        return Path(archive.file_path)
