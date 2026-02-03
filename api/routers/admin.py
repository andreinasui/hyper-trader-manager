"""
Admin router for HyperTrader API.

Provides admin-only endpoints for user and system management.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.middleware.jwt_auth import require_admin
from api.models import User, Trader
from api.schemas.auth import UserResponse
from api.schemas.trader import TraderResponse

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


class SystemStats(BaseModel):
    """System statistics response schema."""

    total_users: int
    total_traders: int
    traders_by_status: dict[str, int]
    users_by_plan: dict[str, int]


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users",
    description="Get a paginated list of all users in the system (admin only).",
)
async def list_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users to return"),
    db: Session = Depends(get_db),
) -> List[UserResponse]:
    """
    List all users with pagination.

    Requires admin privileges.

    - **skip**: Number of users to skip (for pagination)
    - **limit**: Maximum number of users to return (1-1000)

    Returns list of users.
    """
    users = db.query(User).offset(skip).limit(limit).all()

    logger.info(f"Admin listed {len(users)} users")

    return [UserResponse.model_validate(user) for user in users]


@router.get(
    "/traders",
    response_model=List[TraderResponse],
    summary="List all traders system-wide",
    description="Get a paginated list of all traders across all users (admin only).",
)
async def list_all_traders(
    skip: int = Query(0, ge=0, description="Number of traders to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of traders to return"),
    db: Session = Depends(get_db),
) -> List[TraderResponse]:
    """
    List all traders system-wide with pagination.

    Requires admin privileges.

    - **skip**: Number of traders to skip (for pagination)
    - **limit**: Maximum number of traders to return (1-1000)

    Returns list of traders from all users.
    """
    traders = db.query(Trader).offset(skip).limit(limit).all()

    logger.info(f"Admin listed {len(traders)} traders")

    return [TraderResponse.model_validate(trader) for trader in traders]


@router.get(
    "/stats",
    response_model=SystemStats,
    summary="Get system statistics",
    description="Get aggregate statistics about the system (admin only).",
)
async def get_system_stats(
    db: Session = Depends(get_db),
) -> SystemStats:
    """
    Get system-wide statistics.

    Requires admin privileges.

    Returns:
    - Total number of users
    - Total number of traders
    - Traders grouped by status
    - Users grouped by plan tier
    """
    # Count total users
    total_users = db.query(func.count(User.id)).scalar()

    # Count total traders
    total_traders = db.query(func.count(Trader.id)).scalar()

    # Count traders by status
    traders_by_status_query = (
        db.query(Trader.status, func.count(Trader.id)).group_by(Trader.status).all()
    )
    traders_by_status = {status: count for status, count in traders_by_status_query}

    # Count users by plan tier
    users_by_plan_query = (
        db.query(User.plan_tier, func.count(User.id)).group_by(User.plan_tier).all()
    )
    users_by_plan = {plan: count for plan, count in users_by_plan_query}

    logger.info("Admin retrieved system stats")

    return SystemStats(
        total_users=total_users or 0,
        total_traders=total_traders or 0,
        traders_by_status=traders_by_status,
        users_by_plan=users_by_plan,
    )
