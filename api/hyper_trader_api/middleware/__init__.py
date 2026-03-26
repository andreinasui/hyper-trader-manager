"""
Middleware for HyperTrader API.

This package exports authentication middleware.
"""

from hyper_trader_api.middleware.jwt_auth import get_current_user

__all__ = [
    "get_current_user",
]
