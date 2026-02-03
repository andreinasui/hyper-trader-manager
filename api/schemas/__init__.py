"""
Pydantic schemas for HyperTrader API.

This package exports all request/response schemas for API validation.
"""

from api.schemas.auth import (
    UserCreate,
    UserResponse,
    APIKeyCreate,
    APIKeyResponse,
    RegisterResponse,
)
from api.schemas.trader import (
    TraderCreate,
    TraderUpdate,
    TraderResponse,
    TraderListResponse,
    TraderStatusResponse,
    TraderLogsResponse,
    RestartResponse,
    DeleteResponse,
    K8sStatus,
)

__all__ = [
    # Auth schemas
    "UserCreate",
    "UserResponse",
    "APIKeyCreate",
    "APIKeyResponse",
    "RegisterResponse",
    # Trader schemas
    "TraderCreate",
    "TraderUpdate",
    "TraderResponse",
    "TraderListResponse",
    "TraderStatusResponse",
    "TraderLogsResponse",
    "RestartResponse",
    "DeleteResponse",
    "K8sStatus",
]
