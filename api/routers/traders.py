"""
Traders router for HyperTrader API.

Handles trader CRUD operations and management.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.middleware.jwt_auth import get_current_user_flexible
from api.models import User
from api.schemas.trader import (
    DeleteResponse,
    RestartResponse,
    TraderCreate,
    TraderListResponse,
    TraderLogsResponse,
    TraderResponse,
    TraderStatusResponse,
    TraderUpdate,
    K8sStatus,
)
from api.services.trader_service import (
    TraderService,
    TraderServiceError,
    TraderNotFoundError,
    TraderOwnershipError,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/traders",
    tags=["Traders"],
)


def get_trader_service(db: Session = Depends(get_db)) -> TraderService:
    """Dependency to get TraderService instance."""
    return TraderService(db)


def _trader_to_response(trader) -> TraderResponse:
    """Convert Trader model to TraderResponse schema."""
    latest_config = None
    if trader.latest_config:
        latest_config = trader.latest_config.config_json

    return TraderResponse(
        id=trader.id,
        user_id=trader.user_id,
        wallet_address=trader.wallet_address,
        k8s_name=trader.k8s_name,
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
    description=(
        "Create a new trading bot. The trader will be deployed to Kubernetes. "
        "The private key is encrypted and stored securely."
    ),
)
async def create_trader(
    trader_data: TraderCreate,
    user: User = Depends(get_current_user_flexible),
    service: TraderService = Depends(get_trader_service),
) -> TraderResponse:
    """
    Create a new trader.

    - **wallet_address**: Ethereum wallet address (0x + 40 hex chars)
    - **private_key**: Ethereum private key (0x + 64 hex chars) - encrypted and stored securely
    - **config**: Trader configuration JSON
    - **image_tag**: Docker image tag (default: latest)
    """
    try:
        trader = service.create_trader(user.id, trader_data)
        logger.info(f"Trader created: {trader.k8s_name} for user {user.email}")
        return _trader_to_response(trader)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except TraderServiceError as e:
        logger.error(f"Failed to create trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy trader: {str(e)}",
        )


@router.get(
    "/",
    response_model=TraderListResponse,
    summary="List all traders",
    description="List all traders owned by the authenticated user.",
)
async def list_traders(
    user: User = Depends(get_current_user_flexible),
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
    user: User = Depends(get_current_user_flexible),
    service: TraderService = Depends(get_trader_service),
) -> TraderResponse:
    """
    Get a specific trader by ID.
    """
    try:
        trader = service.get_trader(trader_id, user.id)
        return _trader_to_response(trader)

    except TraderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        )
    except TraderOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        )


@router.patch(
    "/{trader_id}",
    response_model=TraderResponse,
    summary="Update trader configuration",
    description="Update a trader's configuration. The pod will be restarted to apply changes.",
)
async def update_trader(
    trader_id: uuid.UUID,
    update_data: TraderUpdate,
    user: User = Depends(get_current_user_flexible),
    service: TraderService = Depends(get_trader_service),
) -> TraderResponse:
    """
    Update a trader's configuration.

    - **config**: New configuration JSON

    The trader pod will be restarted to apply the new configuration.
    """
    try:
        trader = service.update_trader(trader_id, user.id, update_data)
        logger.info(f"Trader updated: {trader.k8s_name}")
        return _trader_to_response(trader)

    except TraderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        )
    except TraderOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        )
    except TraderServiceError as e:
        logger.error(f"Failed to update trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update trader: {str(e)}",
        )


@router.delete(
    "/{trader_id}",
    response_model=DeleteResponse,
    summary="Delete trader",
    description="Delete a trader. This removes all Kubernetes resources and database records.",
)
async def delete_trader(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user_flexible),
    service: TraderService = Depends(get_trader_service),
) -> DeleteResponse:
    """
    Delete a trader.

    This will:
    - Remove the Kubernetes StatefulSet, ConfigMap, and Secret
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

    except TraderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        )
    except TraderOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        )
    except TraderServiceError as e:
        logger.error(f"Failed to delete trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete trader: {str(e)}",
        )


@router.post(
    "/{trader_id}/restart",
    response_model=RestartResponse,
    summary="Restart trader",
    description="Restart a trader's pod.",
)
async def restart_trader(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user_flexible),
    service: TraderService = Depends(get_trader_service),
) -> RestartResponse:
    """
    Restart a trader's pod.

    The pod will be deleted and recreated by the StatefulSet controller.
    """
    try:
        trader = service.get_trader(trader_id, user.id)
        service.restart_trader(trader_id, user.id)
        logger.info(f"Trader restart initiated: {trader.k8s_name}")

        return RestartResponse(
            message="Trader restart initiated",
            trader_id=trader_id,
            k8s_name=trader.k8s_name,
        )

    except TraderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        )
    except TraderOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        )
    except TraderServiceError as e:
        logger.error(f"Failed to restart trader: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restart trader: {str(e)}",
        )


@router.get(
    "/{trader_id}/status",
    response_model=TraderStatusResponse,
    summary="Get trader K8s status",
    description="Get detailed Kubernetes status for a trader.",
)
async def get_trader_status(
    trader_id: uuid.UUID,
    user: User = Depends(get_current_user_flexible),
    service: TraderService = Depends(get_trader_service),
) -> TraderStatusResponse:
    """
    Get detailed Kubernetes status for a trader.

    Returns pod phase, ready status, restart count, and other K8s details.
    """
    try:
        status_data = service.get_trader_status(trader_id, user.id)

        return TraderStatusResponse(
            id=status_data["id"],
            wallet_address=status_data["wallet_address"],
            k8s_name=status_data["k8s_name"],
            status=status_data["status"],
            k8s_status=K8sStatus(**status_data["k8s_status"]),
        )

    except TraderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        )
    except TraderOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        )


@router.get(
    "/{trader_id}/logs",
    response_model=TraderLogsResponse,
    summary="Get trader logs",
    description="Get logs from a trader's pod.",
)
async def get_trader_logs(
    trader_id: uuid.UUID,
    tail_lines: int = Query(
        default=100, ge=1, le=10000, description="Number of log lines to return"
    ),
    user: User = Depends(get_current_user_flexible),
    service: TraderService = Depends(get_trader_service),
) -> TraderLogsResponse:
    """
    Get logs from a trader's pod.

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

    except TraderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trader not found: {trader_id}",
        )
    except TraderOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this trader",
        )
