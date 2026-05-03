# api/hyper_trader_api/schemas/update.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

UpdateStatus = Literal["idle", "updating", "rolled_back", "failed"]


class UpdateStateFile(BaseModel):
    """Schema for the JSON state file at /var/lib/update-state/update-state.json."""

    model_config = ConfigDict(extra="forbid")

    status: UpdateStatus = "idle"
    current_version: str | None = None
    latest_version: str | None = None
    last_checked: datetime | None = None
    update_started_at: datetime | None = None
    old_api_image: str | None = None
    old_web_image: str | None = None
    new_api_image: str | None = None
    new_web_image: str | None = None
    error_message: str | None = None
    finished_at: datetime | None = None


class ServiceStatusEntry(BaseModel):
    image: str | None = None
    running: bool = False
    healthy: bool = False


class ServiceStatus(BaseModel):
    api: ServiceStatusEntry
    web: ServiceStatusEntry


class UpdateStatusResponse(BaseModel):
    current_version: str | None
    latest_version: str | None
    update_available: bool
    last_checked: datetime | None
    status: UpdateStatus
    error_message: str | None
    finished_at: datetime | None
    configured: bool
    service_status: ServiceStatus | None = None


class ApplyUpdateResponse(BaseModel):
    status: UpdateStatus
    message: str
