"""
Traders router for HyperTrader API.

Handles trader CRUD operations and management.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from hyper_trader_api.database import get_db
from hyper_trader_api.middleware.jwt_auth import get_current_user
from hyper_trader_api.models import User
from hyper_trader_api.models.trader import Trader
from hyper_trader_api.schemas.trader import (
    DeleteResponse,
    RestartResponse,
    RuntimeStatus,
    TraderCreate,
    TraderListResponse,
    TraderLogsResponse,
    TraderResponse,
    TraderStatusResponse,
    TraderUpdate,
)
from hyper_trader_api.services.trader_service import (
    TraderNotFoundError,
    TraderOwnershipError,
    TraderService,
    TraderServiceError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/traders",
    tags=["Traders"],
)


def get_trader_service(db: Session = Depends(get_db)) -> TraderService:
    """Dependency to get TraderService instance."""
    return TraderService(db)


def _trader_to_response(trader: Trader) -> TraderResponse:
    """Convert Trader model to TraderResponse schema."""
    latest_config = None
    if trader.latest_config:
        latest_config = trader.latest_config.config_json

    return TraderResponse(
        id=trader.id,
        user_id=trader.user_id,
        wallet_address=trader.wallet_address,
        runtime_name=trader.runtime_name,
        status=trader.status,
        image_tag=trader.image_tag,
        created_at=trader.created_at,
        updated_at=trader.updated_at,
        latest_config=latest_config,
    )


@router.post(
    "/",
    response_model=TraderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trader",
    description=("Create a new trading bot. The trader will be deployed as a Docker container."),
)
async def create_trader(
    trader_data: TraderCreate,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> TraderResponse:
    """
    Create a new trader.

    - **wallet_address**: Ethereum wallet address (0x + 40 hex chars)
    - **config**: Trader configuration JSON
    """
    try:
        trader = service.create_trader(user, trader_data)
        logger.info(f"Trader created: {trader.runtime_name} for user {user.username}")
        return _trader_to_response(trader)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e
    except TraderServiceError as e:
        logger.error(f"Failed to create trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy trader: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=TraderListResponse,
    summary="List all traders",
    description="List all traders owned by the authenticated user.",
)
async def list_traders(
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> TraderListResponse:
    """
    List all traders for the current user.
    """
    traders = service.list_traders(user.id)
    return TraderListResponse(
        traders=[_trader_to_response(t) for t in traders],
        count=len(traders),
    )


@router.get(
    "/{trader_id}",
    response_model=TraderResponse,
    summary="Get trader details",
    description="Get details of a specific trader.",
)
async def get_trader(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> TraderResponse:
    """
    Get a specific trader by ID.
    """
    try:
        trader = service.get_trader(trader_id, user.id)
        return _trader_to_response(trader)

    except TraderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        ) from e
    except TraderOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        ) from e


@router.patch(
    "/{trader_id}",
    response_model=TraderResponse,
    summary="Update trader configuration",
    description="Update a trader's configuration. The container will be restarted to apply changes.",
)
async def update_trader(
    trader_id: uuid.UUID,
    update_data: TraderUpdate,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> TraderResponse:
    """
    Update a trader's configuration.

    - **config**: New configuration JSON

    The trader container will be restarted to apply the new configuration.
    """
    try:
        trader = service.update_trader(trader_id, user.id, update_data)
        logger.info(f"Trader updated: {trader.runtime_name}")
        return _trader_to_response(trader)

    except TraderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        ) from e
    except TraderOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        ) from e
    except TraderServiceError as e:
        logger.error(f"Failed to update trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update trader: {str(e)}",
        ) from e


@router.delete(
    "/{trader_id}",
    response_model=DeleteResponse,
    summary="Delete trader",
    description="Delete a trader. This removes the Docker container and all database records.",
)
async def delete_trader(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> DeleteResponse:
    """
    Delete a trader.

    This will:
    - Stop and remove the Docker container
    - Delete all database records for this trader
    """
    try:
        # Get trader info before deletion for response
        trader = service.get_trader(trader_id, user.id)
        wallet_address = trader.wallet_address

        service.delete_trader(trader_id, user.id)
        logger.info(f"Trader deleted: {trader_id}")

        return DeleteResponse(
            message="Trader deleted successfully",
            trader_id=trader_id,
            wallet_address=wallet_address,
        )

    except TraderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        ) from e
    except TraderOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        ) from e
    except TraderServiceError as e:
        logger.error(f"Failed to delete trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete trader: {str(e)}",
        ) from e


@router.post(
    "/{trader_id}/restart",
    response_model=RestartResponse,
    summary="Restart trader",
    description="Restart a trader's Docker container.",
)
async def restart_trader(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> RestartResponse:
    """
    Restart a trader's Docker container.

    The container will be restarted using Docker API.
    """
    try:
        trader = service.get_trader(trader_id, user.id)
        service.restart_trader(trader_id, user.id)
        logger.info(f"Trader restart initiated: {trader.runtime_name}")

        return RestartResponse(
            message="Trader restart initiated",
            trader_id=trader_id,
            runtime_name=trader.runtime_name,
        )

    except TraderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        ) from e
    except TraderOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        ) from e
    except TraderServiceError as e:
        logger.error(f"Failed to restart trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart trader: {str(e)}",
        ) from e


@router.get(
    "/{trader_id}/status",
    response_model=TraderStatusResponse,
    summary="Get trader runtime status",
    description="Get detailed Docker runtime status for a trader.",
)
async def get_trader_status(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> TraderStatusResponse:
    """
    Get detailed Docker runtime status for a trader.

    Returns container state, running status, start time, and other runtime details.
    """
    try:
        status_data = service.get_trader_status(trader_id, user.id)

        return TraderStatusResponse(
            id=status_data["id"],
            wallet_address=status_data["wallet_address"],
            runtime_name=status_data["runtime_name"],
            status=status_data["status"],
            runtime_status=RuntimeStatus(**status_data["runtime_status"]),
        )

    except TraderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        ) from e
    except TraderOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        ) from e


@router.get(
    "/{trader_id}/logs",
    response_model=TraderLogsResponse,
    summary="Get trader logs",
    description="Get logs from a trader's Docker container.",
)
async def get_trader_logs(
    trader_id: uuid.UUID,
    tail_lines: int = Query(
        default=100, ge=1, le=10000, description="Number of log lines to return"
    ),
    user: User = Depends(get_current_user),
    service: TraderService = Depends(get_trader_service),
) -> TraderLogsResponse:
    """
    Get logs from a trader's Docker container.

    - **tail_lines**: Number of log lines to return (1-10000, default: 100)
    """
    try:
        trader = service.get_trader(trader_id, user.id)
        logs = service.get_trader_logs(trader_id, user.id, tail_lines)

        return TraderLogsResponse(
            trader_id=trader_id,
            wallet_address=trader.wallet_address,
            logs=logs,
            tail_lines=tail_lines,
        )

    except TraderNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        ) from e
    except TraderOwnershipError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        ) from e
