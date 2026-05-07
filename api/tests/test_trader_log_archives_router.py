"""Router tests for /traders/{id}/archives."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def auth_client(client, mock_user):
    """Test client with authentication override."""
    from hyper_trader_api.main import app
    from hyper_trader_api.middleware.session_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield client
    app.dependency_overrides.clear()


def test_list_archives_returns_metadata(auth_client, mock_db, mock_user):
    trader_id = str(uuid.uuid4())
    archive_id = str(uuid.uuid4())

    fake_archive = MagicMock()
    fake_archive.id = archive_id
    fake_archive.trader_id = trader_id
    fake_archive.run_started_at = datetime(2026, 5, 6, 12, 0, tzinfo=UTC)
    fake_archive.run_ended_at = datetime(2026, 5, 6, 13, 0, tzinfo=UTC)
    fake_archive.file_size_bytes = 1234
    fake_archive.created_at = datetime(2026, 5, 6, 13, 0, tzinfo=UTC)
    fake_archive.file_path = "/app/data/logs/X/Y.tar.gz"  # MUST not appear in response

    fake_trader = MagicMock()
    fake_trader.id = trader_id
    fake_trader.user_id = mock_user.id

    with patch(
        "hyper_trader_api.services.trader_service.TraderService.get_trader",
        return_value=fake_trader,
    ):
        with patch(
            "hyper_trader_api.services.log_archive_service.LogArchiveService.list_archives",
            return_value=[fake_archive],
        ):
            resp = auth_client.get(f"/api/v1/traders/{trader_id}/archives")

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 1
    item = body[0]
    assert item["id"] == archive_id
    assert "file_path" not in item
    assert item["file_size_bytes"] == 1234


def test_download_archive_returns_file_with_correct_headers(auth_client, tmp_path, mock_user):
    import io
    import tarfile

    trader_id = str(uuid.uuid4())
    archive_id = str(uuid.uuid4())

    f = tmp_path / "20260506T120000Z.tar.gz"
    log_bytes = b"hello logs\n"
    with tarfile.open(f, "w:gz") as tar:
        info = tarfile.TarInfo(name="20260506T120000Z.log")
        info.size = len(log_bytes)
        tar.addfile(info, io.BytesIO(log_bytes))

    fake_archive = MagicMock()
    fake_archive.id = archive_id
    fake_archive.trader_id = trader_id
    fake_archive.file_path = str(f)
    fake_archive.run_started_at = datetime(2026, 5, 6, 12, 0, tzinfo=UTC)

    fake_trader = MagicMock()
    fake_trader.id = trader_id
    fake_trader.user_id = mock_user.id
    fake_trader.runtime_name = "trader-dl"

    with patch(
        "hyper_trader_api.services.trader_service.TraderService.get_trader",
        return_value=fake_trader,
    ):
        with patch(
            "hyper_trader_api.services.log_archive_service.LogArchiveService.get_archive",
            return_value=fake_archive,
        ):
            resp = auth_client.get(
                f"/api/v1/traders/{trader_id}/archives/{archive_id}/download"
            )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/gzip"
    assert "trader-dl-20260506T120000Z.tar.gz" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"\x1f\x8b")  # gzip magic


def test_download_archive_404_for_other_users_archive(auth_client, mock_user):
    trader_id = str(uuid.uuid4())
    other_trader_id = str(uuid.uuid4())
    archive_id = str(uuid.uuid4())

    fake_trader = MagicMock()
    fake_trader.id = trader_id
    fake_trader.user_id = mock_user.id

    fake_archive = MagicMock()
    fake_archive.id = archive_id
    fake_archive.trader_id = other_trader_id  # belongs to someone else
    fake_archive.file_path = "/tmp/whatever.gz"

    with patch(
        "hyper_trader_api.services.trader_service.TraderService.get_trader",
        return_value=fake_trader,
    ):
        with patch(
            "hyper_trader_api.services.log_archive_service.LogArchiveService.get_archive",
            return_value=fake_archive,
        ):
            resp = auth_client.get(
                f"/api/v1/traders/{trader_id}/archives/{archive_id}/download"
            )

    assert resp.status_code == 404
