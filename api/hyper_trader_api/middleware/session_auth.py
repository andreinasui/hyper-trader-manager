"""
Session authentication middleware for HyperTrader API.

Validates opaque session tokens issued by SessionTokenService,
replacing the previous JWT-based authentication.
"""

import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from hyper_trader_api.database import get_db
from hyper_trader_api.models import User
from hyper_trader_api.services.session_token_service import SessionTokenService

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate user using an opaque session token.

    Extracts the Bearer token from the Authorization header, verifies it
    with SessionTokenService, and retrieves the associated User from the
    database.

    Args:
        request: FastAPI Request object.
        db: Database session (injected by FastAPI).

    Returns:
        User: The authenticated user.

    Raises:
        HTTPException: 401 if the header is missing/malformed, the token is
            invalid or expired, or the user cannot be found in the database.
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract raw token (strip the "Bearer " prefix)
    token = auth_header[len("Bearer ") :]

    # Verify token using SessionTokenService
    service = SessionTokenService(db=db)
    
    try:
        user_id = service.verify_session(token)
    except Exception as e:
        logger.warning("Session token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Look up user by ID returned from the session service
    user = db.query(User).filter_by(id=user_id).first()

    if not user:
        logger.warning("User not found for session token user_id: %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Session token authenticated user: %s", user.username)
    return user
