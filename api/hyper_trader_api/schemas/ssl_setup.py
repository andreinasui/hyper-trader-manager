"""SSL setup request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SSLStatusResponse(BaseModel):
    """Response for SSL setup status check."""

    ssl_configured: bool
    mode: str | None = None  # Loosened to str to tolerate legacy 'ip_only' rows
    domain: str | None = None
    configured_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SSLSetupRequest(BaseModel):
    """Request to configure SSL."""

    mode: Literal["domain"] = Field(
        default="domain",
        description="SSL mode: only 'domain' (Let's Encrypt) is supported",
    )
    domain: str = Field(
        ...,
        pattern=r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$",
        description="Domain name (required)",
    )
    email: EmailStr = Field(
        ...,
        description="Email for Let's Encrypt notifications (required)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"mode": "domain", "domain": "trader.example.com", "email": "admin@example.com"},
            ]
        }
    )


class SSLSetupResponse(BaseModel):
    """Response after SSL setup."""

    success: bool
    message: str
    redirect_url: str | None = None
