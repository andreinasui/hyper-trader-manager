"""
JWT authentication middleware for HyperTrader API.

Supports both JWT Bearer tokens and API key authentication.
"""

import uuid
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models import User
from api.services.auth_service import AuthService
from api.services.jwt_service import JWTService


async def get_current_user_from_jwt(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Extract and validate JWT from Authorization header.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        User if JWT is valid, None otherwise
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")

    # Verify JWT
    payload = JWTService.verify_access_token(token)
    if not payload:
        return None

    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        return None

    user = db.query(User).filter(User.id == user_uuid).first()
    return user


async def get_current_user_from_api_key(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Extract and validate API key from X-API-Key header.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        User if API key is valid, None otherwise
    """
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return None

    # Validate API key
    user = AuthService.get_user_by_api_key(db, api_key)
    return user


async def get_current_user_flexible(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate user using either JWT or API key.

    Tries JWT first, then falls back to API key for backward compatibility.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        User: Authenticated user

    Raises:
        HTTPException: 401 if neither authentication method succeeds
    """
    # Try JWT authentication first
    user = await get_current_user_from_jwt(request, db)

    if user:
        return user

    # Fall back to API key authentication
    user = await get_current_user_from_api_key(request, db)

    if user:
        return user

    # No valid authentication found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(user: User = Depends(get_current_user_flexible)) -> User:
    """
    Dependency that requires the user to be an admin.

    Args:
        user: Current authenticated user

    Returns:
        User: Authenticated admin user

    Raises:
        HTTPException: 403 if user is not an admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )

    return user
