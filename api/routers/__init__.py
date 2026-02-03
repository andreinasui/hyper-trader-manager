"""
API routers for HyperTrader API.

This package exports all API routers.
"""

from api.routers.auth import router as auth_router
from api.routers.traders import router as traders_router
from api.routers.admin import router as admin_router

__all__ = [
    "auth_router",
    "traders_router",
    "admin_router",
]
