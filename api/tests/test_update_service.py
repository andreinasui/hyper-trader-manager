# api/tests/test_update_service.py
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from pytest_httpx import HTTPXMock

from hyper_trader_api.services.update_service import (
    UpdateService,
    is_newer,
    parse_tags,
)

# --- pure helpers ---


def test_parse_tags_filters_pre_releases_and_sorts_desc():
    tags = [
        {"name": "v0.1.1"},
        {"name": "v0.1.2rc1"},
        {"name": "v0.1.10"},
        {"name": "v0.2.0"},
        {"name": "not-a-tag"},
        {"name": "v1.0.0-beta"},
    ]
    assert parse_tags(tags) == ["v0.2.0", "v0.1.10", "v0.1.1"]


def test_is_newer_semver_aware():
    assert is_newer(latest="0.1.10", current="0.1.2") is True
    assert is_newer(latest="0.1.2", current="0.1.10") is False
    assert is_newer(latest="0.1.1", current="0.1.1") is False


# --- state file ---


@pytest.fixture
def service(tmp_path: Path) -> UpdateService:
    return UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path / "stack")


def test_read_state_returns_default_when_missing(service: UpdateService):
    state = service.read_state()
    assert state.status == "idle"
    assert state.current_version is None


def test_write_then_read_round_trips(service: UpdateService):
    state = service.read_state()
    state.status = "updating"
    state.error_message = "oops"
    service.write_state(state)
    again = service.read_state()
    assert again.status == "updating"
    assert again.error_message == "oops"


def test_write_state_is_atomic_and_creates_dir(tmp_path):
    new_dir = tmp_path / "doesnotexist"
    svc = UpdateService(state_dir=new_dir, compose_project_dir=tmp_path)
    svc.write_state(svc.read_state())
    assert (new_dir / "update-state.json").exists()


def test_configured_flag(tmp_path):
    svc_off = UpdateService(state_dir=tmp_path, compose_project_dir=None)
    svc_on = UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path / "stack")
    assert svc_off.configured is False
    assert svc_on.configured is True


# --- fetch_latest_tag ---


def test_fetch_latest_tag_picks_highest_stable(tmp_path, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.github.com/repos/foo/bar/tags?per_page=100",
        json=[
            {"name": "v0.1.1"},
            {"name": "v0.2.0rc1"},
            {"name": "v0.2.0"},
        ],
    )
    svc = UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path)
    assert svc.fetch_latest_tag(repo="foo/bar") == "v0.2.0"


def test_fetch_latest_tag_returns_none_on_empty(tmp_path, httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.github.com/repos/foo/bar/tags?per_page=100",
        json=[],
    )
    svc = UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path)
    assert svc.fetch_latest_tag(repo="foo/bar") is None


def test_fetch_latest_tag_handles_network_error(tmp_path, httpx_mock: HTTPXMock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    svc = UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path)
    assert svc.fetch_latest_tag(repo="foo/bar") is None


# --- spawn_helper ---


def test_spawn_helper_calls_docker_run_with_correct_args(tmp_path):
    docker_client = MagicMock()
    svc = UpdateService(
        state_dir=tmp_path,
        compose_project_dir=tmp_path / "stack",
    )
    svc.spawn_helper(
        client=docker_client,
        helper_image="ghcr.io/h:1",
        old_api_image="api:1",
        old_web_image="web:1",
        new_api_image="api:2",
        new_web_image="web:2",
    )
    docker_client.containers.run.assert_called_once()
    kwargs = docker_client.containers.run.call_args.kwargs
    assert kwargs["image"] == "ghcr.io/h:1"
    assert kwargs["detach"] is True
    assert kwargs["remove"] is True
    assert kwargs["name"] == "hyper-trader-update-helper"
    env = kwargs["environment"]
    assert env["OLD_API_IMAGE"] == "api:1"
    assert env["NEW_API_IMAGE"] == "api:2"
    assert env["NEW_WEB_IMAGE"] == "web:2"
    assert env["COMPOSE_PROJECT_DIR"] == str(tmp_path / "stack")
    vols = kwargs["volumes"]
    assert "/var/run/docker.sock" in vols
    assert str(tmp_path / "stack") in vols
    assert "update-state" in vols  # named volume


def test_spawn_helper_raises_when_not_configured(tmp_path):
    svc = UpdateService(state_dir=tmp_path, compose_project_dir=None)
    with pytest.raises(RuntimeError, match="not configured"):
        svc.spawn_helper(
            client=MagicMock(),
            helper_image="img",
            old_api_image="a",
            old_web_image="b",
            new_api_image="c",
            new_web_image="d",
        )


# --- collect_service_status ---


def test_collect_service_status(tmp_path):
    docker_client = MagicMock()
    api_container = MagicMock()
    api_container.attrs = {
        "Config": {"Image": "api:2"},
        "State": {"Status": "running", "Health": {"Status": "healthy"}},
    }
    web_container = MagicMock()
    web_container.attrs = {
        "Config": {"Image": "web:2"},
        "State": {"Status": "running"},  # no Health key
    }

    def get(name):
        return {"hypertrader-api": api_container, "hypertrader-web": web_container}[name]

    docker_client.containers.get.side_effect = get

    svc = UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path)
    out = svc.collect_service_status(client=docker_client)
    assert out.api.image == "api:2"
    assert out.api.running is True
    assert out.api.healthy is True
    assert out.web.healthy is False  # no health key -> not healthy
    assert out.web.running is True


def test_collect_service_status_handles_missing_container(tmp_path):
    import docker.errors

    docker_client = MagicMock()
    docker_client.containers.get.side_effect = docker.errors.NotFound("nope")
    svc = UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path)
    out = svc.collect_service_status(client=docker_client)
    assert out.api.image is None and out.api.running is False
    assert out.web.image is None and out.web.running is False
