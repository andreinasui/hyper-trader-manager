"""
Authentication schemas for HyperTrader API.

Pydantic v2 schemas for local username/password authentication.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SetupStatusResponse(BaseModel):
    """Setup status response for checking if system is initialized."""

    initialized: bool


class BootstrapRequest(BaseModel):
    """Request to create the first admin user."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8, max_length=255)


class LoginRequest(BaseModel):
    """Login request with username and password."""

    username: str
    password: str


class UserResponse(BaseModel):
    """User information response."""

    id: str
    username: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    """Authentication response with access token and user info."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
