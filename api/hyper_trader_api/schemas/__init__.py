"""
Pydantic schemas for HyperTrader API.

This package exports all request/response schemas for API validation.
"""

from hyper_trader_api.schemas.auth import UserResponse
from hyper_trader_api.schemas.ssl_setup import SSLSetupRequest, SSLSetupResponse, SSLStatusResponse
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

__all__ = [
    # Auth schemas
    "UserResponse",
    # SSL setup schemas
    "SSLStatusResponse",
    "SSLSetupRequest",
    "SSLSetupResponse",
    # Trader schemas
    "TraderCreate",
    "TraderUpdate",
    "TraderResponse",
    "TraderListResponse",
    "TraderStatusResponse",
    "TraderLogsResponse",
    "RestartResponse",
    "DeleteResponse",
    "RuntimeStatus",
]
