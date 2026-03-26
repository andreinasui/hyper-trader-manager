"""
Trader schemas for HyperTrader API.

Pydantic v2 schemas for trader CRUD operations and status.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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
    config: dict[str, Any] = Field(..., description="Trader configuration JSON")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                "private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
                "config": {
                    "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
                    "copy_account": {"address": "0x1234567890abcdef1234567890abcdef12345678"},
                    "order_sizing": {"max_size_usd": 100},
                },
            }
        }
    )


class TraderUpdate(BaseModel):
    """Schema for updating a trader's configuration."""

    config: dict[str, Any] | None = Field(
        default=None, description="Updated trader configuration JSON"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "config": {
                    "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
                    "copy_account": {"address": "0xnewaddress1234567890abcdef12345678901234"},
                    "order_sizing": {"max_size_usd": 200},
                }
            }
        }
    )


class TraderResponse(BaseModel):
    """Schema for trader response."""

    id: uuid.UUID
    user_id: str
    wallet_address: str
    runtime_name: str
    status: str
    image_tag: str
    created_at: datetime
    updated_at: datetime
    latest_config: dict[str, Any] | None = None

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
                    "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"}
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

    state: str = Field(description="Container state (running, exited, not_found, etc.)")
    running: bool = Field(description="Whether the container is running")
    started_at: str | None = Field(default=None, description="ISO timestamp when container started")
    exit_code: int | None = Field(default=None, description="Exit code if container exited")


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
