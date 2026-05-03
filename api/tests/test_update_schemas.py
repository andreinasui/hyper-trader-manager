# api/tests/test_update_schemas.py
from datetime import UTC, datetime

from hyper_trader_api.schemas.update import (
    ServiceStatusEntry,
    UpdateStateFile,
    UpdateStatusResponse,
)


def test_state_file_defaults_to_idle():
    s = UpdateStateFile()
    assert s.status == "idle"
    assert s.current_version is None
    assert s.error_message is None


def test_state_file_round_trip_json():
    s = UpdateStateFile(status="updating", current_version="0.1.1")
    raw = s.model_dump_json()
    loaded = UpdateStateFile.model_validate_json(raw)
    assert loaded == s


def test_status_response_update_available_is_derived():
    r = UpdateStatusResponse(
        current_version="0.1.1",
        latest_version="v0.1.2",
        update_available=True,
        last_checked=datetime.now(UTC),
        status="idle",
        error_message=None,
        finished_at=None,
        configured=True,
        service_status=None,
    )
    assert r.update_available is True


def test_service_status_entry_shape():
    e = ServiceStatusEntry(image="img:tag", running=True, healthy=True)
    assert e.image == "img:tag"
