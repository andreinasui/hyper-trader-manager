"""
Trader schemas for HyperTrader API.

Pydantic v2 schemas for trader CRUD operations and status.
"""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from hyper_trader_api.schemas.trader_config import (
    TraderConfigSchema,
    TraderConfigUpdateSchema,
)


class TraderStatus(str, Enum):
    """Valid trader lifecycle states."""

    CONFIGURED = "configured"
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


class TraderCreate(BaseModel):
    """Schema for creating a new trader."""

    wallet_address: str = Field(
        ...,
        pattern=r"^0x[a-fA-F0-9]{40}$",
        description="Ethereum wallet address (must be 42 characters: 0x followed by 40 hexadecimal characters)",
        json_schema_extra={
            "pattern_description": "Must be a valid Ethereum address (0x + 40 hex characters)"
        },
    )
    private_key: str = Field(
        ...,
        pattern=r"^0x[a-fA-F0-9]{64}$",
        description="Private key for the wallet (0x followed by 64 hexadecimal characters)",
    )
    config: TraderConfigSchema = Field(..., description="Trader configuration")
    name: str | None = Field(
        default=None,
        max_length=50,
        pattern=r"^[a-zA-Z0-9 _-]+$",
        description="User-friendly name for the trader",
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Optional description or notes",
    )
    image_tag: str | None = Field(
        default=None,
        description="Docker image tag to use (e.g. '0.4.4'). If omitted, uses latest local tag.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                "private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "config": {
                    "provider_settings": {
                        "exchange": "hyperliquid",
                        "network": "mainnet",
                        "self_account": {
                            "address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                        },
                        "copy_account": {
                            "address": "0x1234567890abcdef1234567890abcdef12345678",
                        },
                    },
                    "trader_settings": {
                        "min_self_funds": 100,
                        "min_copy_funds": 1000,
                        "trading_strategy": {
                            "type": "order_based",
                        },
                    },
                },
                "image_tag": "0.4.4",
            }
        }
    )


class TraderUpdate(BaseModel):
    """Schema for updating a trader's configuration.

    Note: self_account.address is optional in updates - it will be auto-filled
    from the trader's wallet_address since that's an identity field.
    """

    config: TraderConfigUpdateSchema | None = Field(
        default=None, description="Updated trader configuration"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "config": {
                    "provider_settings": {
                        "exchange": "hyperliquid",
                        "network": "mainnet",
                        "self_account": {
                            "is_sub": False,
                        },
                        "copy_account": {
                            "address": "0xnewaddress1234567890abcdef12345678901234",
                        },
                    },
                    "trader_settings": {
                        "min_self_funds": 200,
                        "min_copy_funds": 2000,
                        "trading_strategy": {
                            "type": "order_based",
                        },
                    },
                }
            }
        }
    )


class TraderInfoUpdate(BaseModel):
    """Schema for updating trader display info (name/description)."""

    name: str | None = Field(
        default=None,
        max_length=50,
        pattern=r"^[a-zA-Z0-9 _-]+$",
        description="User-friendly name for the trader",
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Optional description or notes",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Main Trading Bot",
                "description": "Copy trading setup for testnet",
            }
        }
    )


class TraderResponse(BaseModel):
    """Schema for trader response."""

    id: str
    user_id: str
    wallet_address: str
    runtime_name: str
    status: str
    image_tag: str
    created_at: datetime
    updated_at: datetime
    start_attempts: int = 0
    last_error: str | None = None
    stopped_at: datetime | None = None
    name: str | None = None
    description: str | None = None
    latest_config: TraderConfigSchema | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def display_name(self) -> str:
        """Return name if set, otherwise trader id."""
        return self.name if self.name else self.id

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                "runtime_name": "trader-e221ef33",
                "status": "running",
                "image_tag": "latest",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "latest_config": {
                    "provider_settings": {
                        "exchange": "hyperliquid",
                        "network": "mainnet",
                        "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
                        "copy_account": {"address": "0x1234567890abcdef1234567890abcdef12345678"},
                    },
                    "trader_settings": {
                        "min_self_funds": 100,
                        "min_copy_funds": 1000,
                        "trading_strategy": {
                            "type": "order_based",
                        },
                    },
                },
            }
        },
    )


class TraderListResponse(BaseModel):
    """Schema for listing multiple traders."""

    traders: list[TraderResponse]
    count: int

    model_config = ConfigDict(json_schema_extra={"example": {"traders": [], "count": 0}})


class RuntimeStatus(BaseModel):
    """Docker runtime status details."""

    state: str = Field(description="Container state (running, stopped, failed, pending, etc.)")
    running: bool = Field(description="Whether the container is running")
    started_at: str | None = Field(default=None, description="ISO timestamp when container started")
    exit_code: int | None = Field(default=None, description="Exit code if container exited")
    error: str | None = Field(default=None, description="Error message if task failed")


class TraderStatusResponse(BaseModel):
    """Schema for trader status including Docker runtime details."""

    id: uuid.UUID
    wallet_address: str
    runtime_name: str
    status: str
    runtime_status: RuntimeStatus

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                "runtime_name": "trader-e221ef33",
                "status": "running",
                "runtime_status": {
                    "state": "running",
                    "running": True,
                    "started_at": "2024-01-15T10:30:00Z",
                },
            }
        }
    )


class TraderLogsResponse(BaseModel):
    """Schema for trader logs response."""

    trader_id: uuid.UUID
    wallet_address: str
    logs: str
    tail_lines: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "trader_id": "550e8400-e29b-41d4-a716-446655440000",
                "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                "logs": "2024-01-15 10:30:00 INFO Starting trader...\n2024-01-15 10:30:01 INFO Connected to exchange",
                "tail_lines": 100,
            }
        }
    )


class RestartResponse(BaseModel):
    """Schema for restart response."""

    message: str
    trader_id: uuid.UUID
    runtime_name: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Trader restart initiated",
                "trader_id": "550e8400-e29b-41d4-a716-446655440000",
                "runtime_name": "trader-e221ef33",
            }
        }
    )


class DeleteResponse(BaseModel):
    """Schema for delete response."""

    message: str
    trader_id: uuid.UUID
    wallet_address: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Trader deleted successfully",
                "trader_id": "550e8400-e29b-41d4-a716-446655440000",
                "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
            }
        }
    )


class StartResponse(BaseModel):
    """Schema for start response."""

    message: str
    trader_id: uuid.UUID
    runtime_name: str
    status: str
    start_attempts: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Trader started successfully",
                "trader_id": "550e8400-e29b-41d4-a716-446655440000",
                "runtime_name": "trader-e221ef33",
                "status": "running",
                "start_attempts": 1,
            }
        }
    )


class StopResponse(BaseModel):
    """Schema for stop response."""

    message: str
    trader_id: uuid.UUID
    runtime_name: str
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Trader stopped successfully",
                "trader_id": "550e8400-e29b-41d4-a716-446655440000",
                "runtime_name": "trader-e221ef33",
                "status": "stopped",
            }
        }
    )
