"""
Authentication router for HyperTrader API.

Simple Privy-based authentication with single /me endpoint.
"""

import logging

from fastapi import APIRouter, Depends

from hyper_trader_api.middleware.jwt_auth import get_current_user
from hyper_trader_api.models import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


@router.get(
    "/me",
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user information.

    Returns user info from Privy authentication.
    """
    return {
        "id": current_user.id,
        "privy_user_id": current_user.privy_user_id,
        "wallet_address": current_user.wallet_address,
        "created_at": current_user.created_at.isoformat(),
    }
