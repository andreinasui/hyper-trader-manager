"""
Authentication schemas for HyperTrader API.

Pydantic v2 schemas for Privy-based authentication.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    """User information response."""

    id: str
    privy_user_id: str
    wallet_address: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
