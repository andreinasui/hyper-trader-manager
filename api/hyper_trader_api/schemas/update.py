# api/hyper_trader_api/schemas/update.py
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

UpdateStatus = Literal["idle", "updating", "rolled_back", "failed"]
SubPhase = Literal["host_files", "image_swap"]


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

    # Host-file update fields (added in 0.2.7)
    sub_phase: SubPhase | None = None
    host_files_changed: list[str] = []
    local_edits_overwritten: list[str] = []
    backup_path: str | None = None

    @field_validator("host_files_changed", "local_edits_overwritten", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        # The bash helper writes these as comma-separated strings via jq --arg.
        # Accept both string and list forms.
        if isinstance(v, str):
            return [s for s in v.split(",") if s]
        return v


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

    # Host-file update fields
    sub_phase: SubPhase | None = None
    host_files_changed: list[str] = []
    local_edits_overwritten: list[str] = []
    backup_path: str | None = None


class ApplyUpdateResponse(BaseModel):
    status: UpdateStatus
    message: str
