"""SSL setup request and response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SSLStatusResponse(BaseModel):
    """Response for SSL setup status check."""

    ssl_configured: bool
    mode: Literal["domain", "ip_only"] | None = None
    domain: str | None = None
    configured_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SSLSetupRequest(BaseModel):
    """Request to configure SSL."""

    mode: Literal["domain", "ip_only"] = Field(
        ...,
        description="SSL mode: 'domain' for Let's Encrypt, 'ip_only' for self-signed",
    )
    domain: str | None = Field(
        default=None,
        pattern=r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$",
        description="Domain name (required if mode is 'domain')",
    )
    email: EmailStr | None = Field(
        default=None,
        description="Email for Let's Encrypt notifications (required if mode is 'domain')",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"mode": "domain", "domain": "trader.example.com", "email": "admin@example.com"},
                {"mode": "ip_only"},
            ]
        }
    )


class SSLSetupResponse(BaseModel):
    """Response after SSL setup."""

    success: bool
    message: str
    redirect_url: str | None = None
