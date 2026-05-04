# api/tests/test_updates_router.py
"""Tests for the /api/updates router."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hyper_trader_api.routers.updates import get_docker_client, get_update_service, router
from hyper_trader_api.services.update_service import UpdateService

# ---- helpers ----


def make_app(tmp_path: Path) -> tuple[FastAPI, UpdateService]:
    app = FastAPI()
    svc = UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path / "stack")

    app.include_router(router)
    app.dependency_overrides[get_update_service] = lambda: svc
    app.dependency_overrides[get_docker_client] = lambda: None  # not needed for most tests

    # stub auth
    from hyper_trader_api.middleware.session_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "admin"}

    return app, svc


# ---- GET /api/updates/status ----


def test_status_returns_idle_when_no_state(tmp_path):
    app, svc = make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/api/updates/status")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "idle"
    assert body["configured"] is True
    assert body["update_available"] is False


def test_status_reflects_written_state(tmp_path):
    app, svc = make_app(tmp_path)
    state = svc.read_state()
    state.status = "failed"
    state.current_version = "0.1.1"
    state.latest_version = "v0.2.0"
    state.error_message = "boom"
    svc.write_state(state)
    client = TestClient(app)
    with patch("hyper_trader_api.routers.updates._get_current_version", return_value="0.1.1"):
        r = client.get("/api/updates/status")
    body = r.json()
    assert body["status"] == "failed"
    assert body["error_message"] == "boom"
    assert body["update_available"] is True


def test_status_not_configured(tmp_path):
    app = FastAPI()
    svc = UpdateService(state_dir=tmp_path, compose_project_dir=None)
    app.include_router(router)
    app.dependency_overrides[get_update_service] = lambda: svc
    app.dependency_overrides[get_docker_client] = lambda: None
    from hyper_trader_api.middleware.session_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"id": 1}
    client = TestClient(app)
    r = client.get("/api/updates/status")
    assert r.json()["configured"] is False


# ---- POST /api/updates/apply ----


def test_apply_returns_503_when_not_configured(tmp_path):
    app = FastAPI()
    svc = UpdateService(state_dir=tmp_path, compose_project_dir=None)
    app.include_router(router)
    app.dependency_overrides[get_update_service] = lambda: svc
    app.dependency_overrides[get_docker_client] = lambda: None
    from hyper_trader_api.middleware.session_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {"id": 1}
    client = TestClient(app)
    r = client.post("/api/updates/apply")
    assert r.status_code == 503


def test_apply_returns_409_when_already_updating(tmp_path):
    app, svc = make_app(tmp_path)
    state = svc.read_state()
    state.status = "updating"
    svc.write_state(state)
    client = TestClient(app)
    r = client.post("/api/updates/apply")
    assert r.status_code == 409


def test_apply_returns_400_when_no_update_available(tmp_path):
    app, svc = make_app(tmp_path)
    state = svc.read_state()
    state.current_version = "0.1.0"
    state.latest_version = "v0.1.0"
    svc.write_state(state)
    client = TestClient(app)
    r = client.post("/api/updates/apply")
    assert r.status_code == 400


def test_apply_spawns_helper_when_update_available(tmp_path):
    app, svc = make_app(tmp_path)
    mock_docker = MagicMock()
    app.dependency_overrides[get_docker_client] = lambda: mock_docker

    state = svc.read_state()
    state.current_version = "0.1.0"
    state.latest_version = "v0.2.0"
    svc.write_state(state)

    with (
        patch("hyper_trader_api.routers.updates._get_current_version", return_value="0.1.0"),
        patch.object(svc, "collect_service_status") as mock_status,
        patch.object(svc, "spawn_helper") as mock_spawn,
    ):
        mock_status.return_value = MagicMock(
            api=MagicMock(image="api:0.1.0"),
            web=MagicMock(image="web:0.1.0"),
        )

        client = TestClient(app)
        r = client.post("/api/updates/apply")

    assert r.status_code == 200
    mock_spawn.assert_called_once()
    # state should be set to updating
    new_state = svc.read_state()
    assert new_state.status == "updating"


# ---- POST /api/updates/acknowledge ----


def test_acknowledge_clears_failed_state(tmp_path):
    app, svc = make_app(tmp_path)
    state = svc.read_state()
    state.status = "failed"
    state.error_message = "old error"
    svc.write_state(state)
    client = TestClient(app)
    r = client.post("/api/updates/acknowledge")
    assert r.status_code == 200
    assert svc.read_state().status == "idle"
    assert svc.read_state().error_message is None


def test_acknowledge_noop_when_idle(tmp_path):
    app, svc = make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/api/updates/acknowledge")
    assert r.status_code == 200
    assert svc.read_state().status == "idle"


# ---- POST /api/updates/check ----


def test_check_triggers_version_fetch(tmp_path):
    app, svc = make_app(tmp_path)
    with patch.object(svc, "fetch_latest_tag", return_value="v0.2.0"):
        state = svc.read_state()
        state.current_version = "0.1.0"
        svc.write_state(state)
        client = TestClient(app)
        r = client.post("/api/updates/check")
    assert r.status_code == 200
    assert svc.read_state().latest_version == "v0.2.0"
