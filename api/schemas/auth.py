"""
Authentication and user schemas for HyperTrader API.

Pydantic v2 schemas for user registration and API key management.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    password: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "trader@example.com", "password": "securepassword123"}
        }
    )


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive data)."""

    id: uuid.UUID
    email: str
    plan_tier: str
    is_admin: bool
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "trader@example.com",
                "plan_tier": "free",
                "is_admin": False,
                "created_at": "2024-01-15T10:30:00Z",
            }
        },
    )


class APIKeyCreate(BaseModel):
    """Schema for requesting a new API key (empty, triggers generation)."""

    model_config = ConfigDict(json_schema_extra={"example": {}})


class APIKeyResponse(BaseModel):
    """
    Schema for API key response.

    WARNING: The api_key is returned ONLY once upon creation/regeneration.
    It is not stored in plaintext and cannot be retrieved later.
    """

    api_key: str
    message: str = "Store this API key securely - it will not be shown again"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "api_key": "ht_a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
                "message": "Store this API key securely - it will not be shown again",
            }
        }
    )


class RegisterResponse(BaseModel):
    """Schema for registration response (user + initial API key)."""

    user: UserResponse
    api_key: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    message: str = "User registered successfully"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "trader@example.com",
                    "plan_tier": "free",
                    "is_admin": False,
                    "created_at": "2024-01-15T10:30:00Z",
                },
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "message": "User registered successfully",
            }
        }
    )


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "trader@example.com", "password": "securepassword123"}
        }
    )


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "trader@example.com",
                    "plan_tier": "free",
                    "is_admin": False,
                    "created_at": "2024-01-15T10:30:00Z",
                },
            }
        }
    )


class RefreshRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}}
    )


class RefreshResponse(BaseModel):
    """Schema for refresh token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 900,
            }
        }
    )
