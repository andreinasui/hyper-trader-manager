"""
SSL setup router for HyperTrader API.

Provides endpoints for configuring SSL/HTTPS during initial setup.
No authentication required - this is a first-time setup operation.
"""

import logging
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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

    Returns:
        SSLStatusResponse: ssl_configured flag, mode, domain, and configured_at timestamp
    """
    service = SSLSetupService(db)
    config = service.get_ssl_config()

    if config is None:
        return SSLStatusResponse(ssl_configured=False)

    return SSLStatusResponse(
        ssl_configured=True,
        mode=cast(Literal["domain", "ip_only"], config.mode),
        domain=config.domain,
        configured_at=config.configured_at,
    )


@router.post(
    "/ssl",
    response_model=SSLSetupResponse,
    summary="Configure SSL/HTTPS",
    description=(
        "Configure SSL/HTTPS for the application. "
        "Use mode='domain' for Let's Encrypt certificates or mode='ip_only' for self-signed."
    ),
)
async def configure_ssl(
    request: SSLSetupRequest,
    db: Session = Depends(get_db),
) -> SSLSetupResponse:
    """
    Configure SSL/HTTPS.

    Args:
        request: SSLSetupRequest with mode, optional domain and email
        db: Database session

    Returns:
        SSLSetupResponse: success flag, message, and optional redirect_url

    Raises:
        HTTPException: 400 if SSL is already configured
        HTTPException: 422 if mode='domain' but domain or email is missing
        HTTPException: 500 if SSL setup fails
    """
    service = SSLSetupService(db)

    # Check if already configured
    if service.is_ssl_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SSL is already configured",
        )

    # Validate domain mode requirements
    if request.mode == "domain":
        if not request.domain:
            raise HTTPException(
                status_code=422,
                detail="domain is required when mode is 'domain'",
            )
        if not request.email:
            raise HTTPException(
                status_code=422,
                detail="email is required when mode is 'domain'",
            )

    try:
        if request.mode == "domain":
            redirect_url = service.configure_domain_ssl(
                domain=request.domain,  # type: ignore[arg-type]
                email=str(request.email),
            )
            return SSLSetupResponse(
                success=True,
                message=f"SSL configured for domain {request.domain}. Redirecting to HTTPS...",
                redirect_url=redirect_url,
            )
        else:
            message = service.configure_ip_only_ssl()
            return SSLSetupResponse(
                success=True,
                message=message,
                redirect_url=None,
            )

    except SSLSetupError as e:
        logger.error(f"SSL setup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
