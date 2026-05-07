"""Tests for LogArchiveService."""

from __future__ import annotations

import io
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hyper_trader_api.models import Trader, TraderLogArchive


@pytest.fixture
def fake_trader() -> Trader:
    t = Trader(
        id="11111111-1111-1111-1111-111111111111",
        user_id="00000000-0000-0000-0000-000000000000",
        wallet_address="0xabc",
        runtime_name="trader-test",
        last_started_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=UTC),
    )
    return t


def test_archive_run_writes_tar_gz_file_and_db_row(tmp_path: Path, fake_trader: Trader) -> None:
    from hyper_trader_api.services.log_archive_service import LogArchiveService

    runtime = MagicMock()
    runtime.get_logs.return_value = "line one\nline two\n"

    db = MagicMock()

    svc = LogArchiveService(db=db, archive_dir=tmp_path, runtime=runtime)
    archive = svc.archive_run(fake_trader)

    assert archive is not None
    assert isinstance(archive, TraderLogArchive)
    assert archive.trader_id == fake_trader.id
    assert archive.run_started_at == fake_trader.last_started_at

    file_path = Path(archive.file_path)
    assert file_path.exists()
    assert file_path.suffix == ".gz"
    assert file_path.name == "20260506T120000Z.tar.gz"
    assert file_path.parent == tmp_path / fake_trader.id

    with tarfile.open(file_path, "r:gz") as tar:
        member = tar.getmembers()[0]
        assert member.name == "20260506T120000Z.log"
        extracted = tar.extractfile(member)
        assert extracted is not None
        assert extracted.read().decode("utf-8") == "line one\nline two\n"

    assert archive.file_size_bytes == file_path.stat().st_size

    runtime.get_logs.assert_called_once_with(fake_trader.runtime_name, all_lines=True)
    db.add.assert_called_once_with(archive)
    db.commit.assert_called_once()


def test_archive_run_skips_when_no_logs(tmp_path: Path, fake_trader: Trader) -> None:
    from hyper_trader_api.services.log_archive_service import LogArchiveService

    runtime = MagicMock()
    runtime.get_logs.return_value = ""

    db = MagicMock()

    svc = LogArchiveService(db=db, archive_dir=tmp_path, runtime=runtime)
    result = svc.archive_run(fake_trader)

    assert result is None
    db.add.assert_not_called()
    db.commit.assert_not_called()

    # No tmp files left
    tmp_files = list(tmp_path.rglob("*.tmp"))
    assert tmp_files == []


def test_archive_run_falls_back_to_now_if_no_last_started_at(
    tmp_path: Path, fake_trader: Trader, caplog: pytest.LogCaptureFixture
) -> None:
    from hyper_trader_api.services.log_archive_service import LogArchiveService

    fake_trader.last_started_at = None

    runtime = MagicMock()
    runtime.get_logs.return_value = "some log output\n"

    db = MagicMock()

    svc = LogArchiveService(db=db, archive_dir=tmp_path, runtime=runtime)
    archive = svc.archive_run(fake_trader)

    assert archive is not None
    assert "no last_started_at" in caplog.text


def test_archive_run_cleans_tmp_on_failure(tmp_path: Path, fake_trader: Trader) -> None:
    from hyper_trader_api.services.log_archive_service import LogArchiveService

    runtime = MagicMock()
    runtime.get_logs.return_value = "line one\nline two\n"

    db = MagicMock()
    db.commit.side_effect = RuntimeError("DB exploded")

    svc = LogArchiveService(db=db, archive_dir=tmp_path, runtime=runtime)

    with pytest.raises(RuntimeError, match="DB exploded"):
        svc.archive_run(fake_trader)

    trader_dir = tmp_path / fake_trader.id
    tmp_files = list(trader_dir.glob("*.tmp")) if trader_dir.exists() else []
    assert tmp_files == []


def test_purge_trader_removes_directory(tmp_path: Path, fake_trader: Trader) -> None:
    from hyper_trader_api.services.log_archive_service import LogArchiveService

    runtime = MagicMock()
    runtime.get_logs.return_value = "line one\nline two\n"

    db = MagicMock()

    svc = LogArchiveService(db=db, archive_dir=tmp_path, runtime=runtime)
    svc.archive_run(fake_trader)

    trader_dir = tmp_path / fake_trader.id
    assert trader_dir.exists()

    svc.purge_trader(fake_trader.id)
    assert not trader_dir.exists()


def test_purge_trader_is_idempotent(tmp_path: Path, fake_trader: Trader) -> None:
    from hyper_trader_api.services.log_archive_service import LogArchiveService

    db = MagicMock()
    runtime = MagicMock()

    svc = LogArchiveService(db=db, archive_dir=tmp_path, runtime=runtime)
    # Should not raise even though the directory doesn't exist
    svc.purge_trader("nonexistent-trader-id")
