"""
Authentication router for HyperTrader API.

Local username/password authentication.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from hyper_trader_api.database import get_db
from hyper_trader_api.middleware.session_auth import get_current_user
from hyper_trader_api.models import User
from hyper_trader_api.schemas.auth import (
    AuthResponse,
    BootstrapRequest,
    LoginRequest,
    SetupStatusResponse,
    UserResponse,
)
from hyper_trader_api.services.local_auth_service import LocalAuthService
from hyper_trader_api.services.session_token_service import SessionTokenService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


@router.get(
    "/setup-status",
    response_model=SetupStatusResponse,
    summary="Check system initialization status",
    description="Check if the system has been initialized with at least one user.",
)
async def get_setup_status(
    db: Session = Depends(get_db),
) -> SetupStatusResponse:
    """
    Check if system is initialized.

    Returns:
        SetupStatusResponse: initialized=True if any user exists, False otherwise
    """
    auth_service = LocalAuthService(db)
    initialized = auth_service.system_initialized()

    return SetupStatusResponse(initialized=initialized)


@router.post(
    "/bootstrap",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bootstrap the first admin user",
    description="Create the first admin user during initial system setup. Can only be called once.",
)
async def bootstrap_admin(
    request: BootstrapRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """
    Bootstrap the system with the first admin user.

    This endpoint can only be called once - when no users exist.
    Subsequent calls will return 409 Conflict.

    Args:
        request: BootstrapRequest with username and password
        db: Database session

    Returns:
        AuthResponse: Access token and user info

    Raises:
        HTTPException: 409 if system is already initialized
    """
    auth_service = LocalAuthService(db)
    token_service = SessionTokenService(db)

    try:
        # Create admin user
        user = auth_service.bootstrap_admin(request.username, request.password)

        # Generate session token
        access_token = token_service.create_session(user)

        logger.info(f"System bootstrapped with admin user: {user.username}")

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    except ValueError as e:
        # System already initialized or validation error
        logger.warning(f"Bootstrap attempt failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with username and password",
    description="Authenticate with username and password to receive an access token.",
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """
    Authenticate user with username and password.

    Args:
        request: LoginRequest with username and password
        db: Database session

    Returns:
        AuthResponse: Access token and user info

    Raises:
        HTTPException: 401 if credentials are invalid
    """
    auth_service = LocalAuthService(db)
    token_service = SessionTokenService(db)

    # Authenticate user
    user = auth_service.authenticate(request.username, request.password)

    if not user:
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate session token
    access_token = token_service.create_session(user)

    logger.info(f"User logged in: {user.username}")

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user information.

    Requires valid session token in Authorization header.

    Args:
        current_user: Current authenticated user (from session token)

    Returns:
        UserResponse: Current user information
    """
    return UserResponse.model_validate(current_user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and revoke session",
    description="Revoke the current session token.",
)
async def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Logout and revoke current session token."""
    auth_header = request.headers.get("Authorization", "")
    # Extract token using slice (not replace) to handle only the prefix
    token = auth_header[len("Bearer ") :] if auth_header.startswith("Bearer ") else ""

    token_service = SessionTokenService(db)
    token_service.revoke_session(token)

    logger.info(f"User logged out: {current_user.username}")
