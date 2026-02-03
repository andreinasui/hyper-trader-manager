"""
Middleware for HyperTrader API.

This package exports authentication middleware.
"""

from api.middleware.api_key_auth import get_current_user

__all__ = [
    "get_current_user",
]
