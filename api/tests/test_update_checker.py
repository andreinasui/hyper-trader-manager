# api/tests/test_update_checker.py
"""Tests for the background update checker worker."""

import asyncio
from unittest.mock import patch

import pytest

from hyper_trader_api.workers.update_checker import UpdateChecker


@pytest.fixture
def service(tmp_path):
    from hyper_trader_api.services.update_service import UpdateService

    return UpdateService(state_dir=tmp_path, compose_project_dir=tmp_path / "stack")


@pytest.fixture
def checker(service):
    return UpdateChecker(service=service, repo="owner/repo", interval=0)


@pytest.mark.asyncio
async def test_run_once_sets_latest_version_when_newer(checker, service):
    with patch.object(service, "fetch_latest_tag", return_value="v0.2.0"):
        state = service.read_state()
        state.current_version = "0.1.0"
        service.write_state(state)
        await checker.run_once()
    state = service.read_state()
    assert state.latest_version == "v0.2.0"
    assert state.last_checked is not None


@pytest.mark.asyncio
async def test_run_once_no_update_when_current_is_latest(checker, service):
    with patch.object(service, "fetch_latest_tag", return_value="v0.1.0"):
        state = service.read_state()
        state.current_version = "0.1.0"
        service.write_state(state)
        await checker.run_once()
    state = service.read_state()
    assert state.latest_version == "v0.1.0"
    assert state.last_checked is not None


@pytest.mark.asyncio
async def test_run_once_skips_when_status_is_updating(checker, service):
    with patch.object(service, "fetch_latest_tag", return_value="v0.2.0") as mock_fetch:
        state = service.read_state()
        state.status = "updating"
        state.current_version = "0.1.0"
        service.write_state(state)
        await checker.run_once()
        mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_run_once_handles_fetch_failure_gracefully(checker, service):
    with patch.object(service, "fetch_latest_tag", return_value=None):
        state = service.read_state()
        state.current_version = "0.1.0"
        service.write_state(state)
        await checker.run_once()
    # state unchanged except last_checked updated
    state = service.read_state()
    assert state.last_checked is not None


@pytest.mark.asyncio
async def test_start_stop_loop(checker):
    run_once_calls = []

    async def fake_run_once():
        run_once_calls.append(1)

    checker.run_once = fake_run_once
    task = asyncio.create_task(checker.start())
    await asyncio.sleep(0.05)
    checker.stop()
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert len(run_once_calls) >= 1
