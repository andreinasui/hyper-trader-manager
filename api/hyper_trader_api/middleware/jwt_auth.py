"""
Privy JWT authentication middleware for HyperTrader API.

Validates Privy JWT tokens and creates/retrieves users.
"""

import logging

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from hyper_trader_api.database import get_db
from hyper_trader_api.models import User
from hyper_trader_api.services.privy_service import PrivyError, get_privy_service

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate user using Privy JWT token.

    Extracts Bearer token from Authorization header, verifies it with Privy,
    and creates or retrieves the user from the database.

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

    # Verify token with Privy
    privy_service = get_privy_service()

    try:
        payload = privy_service.verify_access_token(token)
        privy_user_id = payload.get("sub")

        if not privy_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except PrivyError as e:
        logger.warning(f"Privy token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    # Check if user exists
    user = db.query(User).filter(User.privy_user_id == privy_user_id).first()

    if user:
        logger.debug(f"Existing user authenticated: {privy_user_id}")
        return user

    # User doesn't exist - create new user
    try:
        # Fetch wallet address from Privy
        wallet_address = await privy_service.get_wallet_address(privy_user_id)

        # Create new user
        user = User(
            privy_user_id=privy_user_id,
            wallet_address=wallet_address,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"New user created from Privy: {privy_user_id} - {wallet_address}")
        return user

    except PrivyError as e:
        logger.error(f"Failed to fetch user info from Privy: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user information",
        ) from e
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account",
        ) from e
