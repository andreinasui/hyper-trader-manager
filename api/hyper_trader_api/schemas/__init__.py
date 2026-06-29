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
from hyper_trader_api.schemas.trader_config import (
    AutoBucketConfig,
    BucketConfig,
    CopyAccount,
    ManualBucketConfig,
    OpenOnLowPnl,
    OrderBasedRiskParameters,
    OrderBasedStrategy,
    PositionBasedStrategy,
    ProviderRiskParameters,
    ProviderSettings,
    SelfAccount,
    TraderConfigSchema,
    TraderSettings,
    TradingStrategy,
)
from hyper_trader_api.schemas.trader_log_archive import TraderLogArchiveResponse

__all__ = [
    # Auth schemas
    "UserResponse",
    # Trader log archive schemas
    "TraderLogArchiveResponse",
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
    # Trader config schemas
    "TraderConfigSchema",
    "ProviderSettings",
    "ProviderRiskParameters",
    "SelfAccount",
    "CopyAccount",
    "TraderSettings",
    "TradingStrategy",
    "PositionBasedStrategy",
    "OrderBasedStrategy",
    "OrderBasedRiskParameters",
    "OpenOnLowPnl",
    "BucketConfig",
    "ManualBucketConfig",
    "AutoBucketConfig",
]
