"""
Images router for HyperTrader API.

Provides image version information for the trader Docker image.
"""

import logging

from fastapi import APIRouter, Depends

from hyper_trader_api.middleware.session_auth import get_current_user
from hyper_trader_api.models import User
from hyper_trader_api.schemas.image import ImageVersionInfo
from hyper_trader_api.services.image_service import ImageService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/images",
    tags=["Images"],
)


@router.get(
    "",
    response_model=ImageVersionInfo,
    summary="Get image version information",
    description=(
        "Returns local and remote image version data for the trader Docker image. "
        "Remote data is fetched from the public GHCR registry."
    ),
)
async def get_image_versions(
    current_user: User = Depends(get_current_user),
) -> ImageVersionInfo:
    """Get image version information (local + remote from public GHCR)."""
    service = ImageService()
    return service.get_image_versions()
