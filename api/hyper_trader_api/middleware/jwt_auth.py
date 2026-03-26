"""
Local JWT authentication middleware for HyperTrader API.

Validates JWT tokens issued by the local auth service.
"""

import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.database import get_db
from hyper_trader_api.models import User
from hyper_trader_api.services.token_service import TokenService

logger = logging.getLogger(__name__)
settings = get_settings()


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate user using local JWT token.

    Extracts Bearer token from Authorization header, verifies it with TokenService,
    and retrieves the user from the database.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        User: Authenticated user

    Raises:
        HTTPException: 401 if authentication fails
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token
    token = auth_header.replace("Bearer ", "")

    # Verify token with TokenService
    token_service = TokenService(settings.jwt_secret_key)

    try:
        payload = token_service.verify_access_token(token)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Look up user by ID from token
    user = db.query(User).filter_by(id=user_id).first()

    if not user:
        logger.warning(f"User not found for ID in token: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug(f"User authenticated: {user.username}")
    return user
