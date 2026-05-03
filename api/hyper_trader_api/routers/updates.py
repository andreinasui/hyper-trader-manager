# api/hyper_trader_api/routers/updates.py
from __future__ import annotations

import logging
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Annotated

import docker
import docker.errors
from fastapi import APIRouter, Depends, HTTPException

from hyper_trader_api.config import Settings, get_settings
from hyper_trader_api.middleware.session_auth import get_current_user
from hyper_trader_api.schemas.update import ApplyUpdateResponse, UpdateStatusResponse
from hyper_trader_api.services.update_service import UpdateService, is_newer

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/updates", tags=["updates"])


# ---- injectable dependencies ----


def get_update_service(settings: Annotated[Settings, Depends(get_settings)]) -> UpdateService:
    return UpdateService(
        state_dir=settings.update_state_dir,
        compose_project_dir=settings.compose_project_dir,
    )


def get_docker_client():
    try:
        return docker.from_env()
    except Exception:
        return None


def _get_current_version(state_current: str | None) -> str | None:
    try:
        return version("hyper-trader-api")
    except PackageNotFoundError:
        return state_current


# ---- endpoints ----


@router.get("/status", response_model=UpdateStatusResponse)
async def get_status(
    _user=Depends(get_current_user),
    svc: UpdateService = Depends(get_update_service),
    docker_client=Depends(get_docker_client),
):
    state = svc.read_state()
    current = _get_current_version(state.current_version)
    latest = state.latest_version

    update_available = False
    if current and latest:
        try:
            update_available = is_newer(latest.lstrip("v"), current.lstrip("v"))
        except Exception:
            pass

    service_status = None
    if docker_client is not None:
        try:
            service_status = svc.collect_service_status(client=docker_client)
        except Exception:
            log.warning("Failed to collect service status", exc_info=True)

    return UpdateStatusResponse(
        current_version=current,
        latest_version=latest,
        update_available=update_available,
        last_checked=state.last_checked,
        status=state.status,
        error_message=state.error_message,
        finished_at=state.finished_at,
        configured=svc.configured,
        service_status=service_status,
    )


@router.post("/apply", response_model=ApplyUpdateResponse)
async def apply_update(
    _user=Depends(get_current_user),
    svc: UpdateService = Depends(get_update_service),
    docker_client=Depends(get_docker_client),
    settings: Settings = Depends(get_settings),
):
    if not svc.configured:
        raise HTTPException(status_code=503, detail="Update system not configured")

    state = svc.read_state()

    if state.status == "updating":
        raise HTTPException(status_code=409, detail="Update already in progress")

    current = _get_current_version(state.current_version)
    latest = state.latest_version

    if not latest or not current or not is_newer(latest.lstrip("v"), current.lstrip("v")):
        raise HTTPException(status_code=400, detail="No update available")

    # Collect current images for rollback
    svc_status = svc.collect_service_status(client=docker_client)

    state.status = "updating"
    state.current_version = current
    state.old_api_image = svc_status.api.image
    state.old_web_image = svc_status.web.image
    state.new_api_image = f"ghcr.io/andreinasui/hyper-trader-manager-api:{latest.lstrip('v')}"
    state.new_web_image = f"ghcr.io/andreinasui/hyper-trader-manager-web:{latest.lstrip('v')}"
    state.error_message = None
    svc.write_state(state)

    svc.spawn_helper(
        client=docker_client,
        helper_image=settings.helper_image or "",
        old_api_image=state.old_api_image or "",
        old_web_image=state.old_web_image or "",
        new_api_image=state.new_api_image,
        new_web_image=state.new_web_image,
    )

    return ApplyUpdateResponse(status="updating", message="Update started")


@router.post("/acknowledge", response_model=ApplyUpdateResponse)
async def acknowledge(
    _user=Depends(get_current_user),
    svc: UpdateService = Depends(get_update_service),
):
    state = svc.read_state()
    if state.status in {"failed", "rolled_back"}:
        state.status = "idle"
        state.error_message = None
        svc.write_state(state)
    return ApplyUpdateResponse(status="idle", message="Acknowledged")


@router.post("/check", response_model=UpdateStatusResponse)
async def check_now(
    _user=Depends(get_current_user),
    svc: UpdateService = Depends(get_update_service),
    docker_client=Depends(get_docker_client),
    settings: Settings = Depends(get_settings),
):
    if settings.github_repo:
        latest = svc.fetch_latest_tag(repo=settings.github_repo)
        state = svc.read_state()
        state.last_checked = datetime.now(UTC)
        if latest:
            state.latest_version = latest
        svc.write_state(state)

    # Return current status
    state = svc.read_state()
    current = _get_current_version(state.current_version)
    latest = state.latest_version
    update_available = False
    if current and latest:
        try:
            update_available = is_newer(latest.lstrip("v"), current.lstrip("v"))
        except Exception:
            pass

    service_status = None
    if docker_client is not None:
        try:
            service_status = svc.collect_service_status(client=docker_client)
        except Exception:
            pass

    return UpdateStatusResponse(
        current_version=current,
        latest_version=state.latest_version,
        update_available=update_available,
        last_checked=state.last_checked,
        status=state.status,
        error_message=state.error_message,
        finished_at=state.finished_at,
        configured=svc.configured,
        service_status=service_status,
    )
