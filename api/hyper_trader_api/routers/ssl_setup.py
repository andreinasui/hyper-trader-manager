"""
SSL setup router for HyperTrader API.

Provides endpoints for configuring SSL/HTTPS during initial setup.
No authentication required - this is a first-time setup operation.
"""

import logging
from typing import Literal, cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.database import get_db
from hyper_trader_api.schemas.ssl_setup import SSLSetupRequest, SSLSetupResponse, SSLStatusResponse
from hyper_trader_api.services.ssl_setup_service import SSLSetupError, SSLSetupService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/setup",
    tags=["Setup"],
)


@router.get(
    "/ssl-status",
    response_model=SSLStatusResponse,
    summary="Check SSL configuration status",
    description="Check whether SSL has been configured and return current mode, domain, and timestamp.",
)
async def get_ssl_status(
    db: Session = Depends(get_db),
) -> SSLStatusResponse:
    """
    Check current SSL configuration status.

    In development mode, always returns ssl_configured=True to skip SSL setup.

    Returns:
        SSLStatusResponse: ssl_configured flag, mode, domain, and configured_at timestamp
    """
    settings = get_settings()

    # In development mode, skip SSL setup requirement entirely
    if settings.environment == "development":
        return SSLStatusResponse(ssl_configured=True, mode="domain")

    service = SSLSetupService(db)
    config = service.get_ssl_config()

    if config is None:
        return SSLStatusResponse(ssl_configured=False)

    return SSLStatusResponse(
        ssl_configured=True,
        mode=cast(Literal["domain"], config.mode),
        domain=config.domain,
        configured_at=config.configured_at,
    )


@router.post(
    "/ssl",
    response_model=SSLSetupResponse,
    summary="Configure SSL/HTTPS",
    description=("Configure SSL/HTTPS for the application using Let's Encrypt certificates."),
)
async def configure_ssl(
    request: SSLSetupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SSLSetupResponse:
    """
    Configure SSL/HTTPS.

    Writes Traefik config + persists DB row synchronously, then schedules the
    Traefik container restart as a FastAPI background task. The restart MUST
    run after the response is flushed: restarting Traefik severs the in-flight
    request connection (the browser sees NetworkError) if done inline.

    Args:
        request: SSLSetupRequest with domain and email
        background_tasks: FastAPI BackgroundTasks (for deferred Traefik restart)
        db: Database session

    Returns:
        SSLSetupResponse: success flag, message, and redirect_url

    Raises:
        HTTPException: 403 if not in production
        HTTPException: 400 if SSL is already configured
        HTTPException: 500 if SSL setup fails
    """
    settings = get_settings()
    if settings.environment != "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SSL setup is only available in production environment",
        )

    service = SSLSetupService(db)

    # Check if already configured
    if service.is_ssl_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSL is already configured",
        )

    try:
        redirect_url = service.configure_domain_ssl(
            domain=request.domain,
            email=str(request.email),
        )
        # Defer Traefik restart until after response is flushed to the client.
        # Restarting inline would sever the in-flight TCP connection (NetworkError).
        background_tasks.add_task(service.restart_traefik)
        return SSLSetupResponse(
            success=True,
            message=f"SSL configured for domain {request.domain}. Redirecting to HTTPS...",
            redirect_url=redirect_url,
        )

    except SSLSetupError as e:
        logger.error(f"SSL setup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
