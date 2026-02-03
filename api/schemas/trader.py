"""
Trader schemas for HyperTrader API.

Pydantic v2 schemas for trader CRUD operations and status.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

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
        description="Ethereum private key (must be 66 characters: 0x followed by 64 hexadecimal characters)",
        json_schema_extra={
            "pattern_description": "Must be a valid Ethereum private key (0x + 64 hex characters)"
        },
    )
    config: Dict[str, Any] = Field(..., description="Trader configuration JSON")
    image_tag: Optional[str] = Field(
        default="latest", description="Docker image tag for the trader"
    )

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
                "image_tag": "latest",
            }
        }
    )


class TraderUpdate(BaseModel):
    """Schema for updating a trader's configuration."""

    config: Optional[Dict[str, Any]] = Field(
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
    user_id: uuid.UUID
    wallet_address: str
    k8s_name: str
    status: str
    image_tag: str
    created_at: datetime
    updated_at: datetime
    latest_config: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "550e8400-e29b-41d4-a716-446655440001",
                "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                "k8s_name": "trader-e221ef33",
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

    traders: List[TraderResponse]
    count: int

    model_config = ConfigDict(json_schema_extra={"example": {"traders": [], "count": 0}})


class K8sStatus(BaseModel):
    """Kubernetes status details."""

    pod_phase: str = Field(description="Pod phase (Pending, Running, Succeeded, Failed, Unknown)")
    ready: bool = Field(description="Whether the pod is ready")
    restarts: int = Field(description="Number of container restarts")
    pod_ip: Optional[str] = None
    node: Optional[str] = None
    started_at: Optional[str] = None


class TraderStatusResponse(BaseModel):
    """Schema for trader status including K8s details."""

    id: uuid.UUID
    wallet_address: str
    k8s_name: str
    status: str
    k8s_status: K8sStatus

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
                "k8s_name": "trader-e221ef33",
                "status": "running",
                "k8s_status": {
                    "pod_phase": "Running",
                    "ready": True,
                    "restarts": 0,
                    "pod_ip": "10.42.0.15",
                    "node": "k3s-node-1",
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
    k8s_name: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Trader restart initiated",
                "trader_id": "550e8400-e29b-41d4-a716-446655440000",
                "k8s_name": "trader-e221ef33",
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
