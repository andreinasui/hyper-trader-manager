"""
Authentication router for HyperTrader API.

Local username/password authentication for self-hosted deployment.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.database import get_db
from hyper_trader_api.middleware.jwt_auth import get_current_user
from hyper_trader_api.models import User
from hyper_trader_api.schemas.auth import (
    AuthResponse,
    BootstrapRequest,
    LoginRequest,
    SetupStatusResponse,
    UserResponse,
)
from hyper_trader_api.services.local_auth_service import LocalAuthService
from hyper_trader_api.services.token_service import TokenService

logger = logging.getLogger(__name__)
settings = get_settings()

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
):
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
):
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
    token_service = TokenService(settings.jwt_secret_key)
    
    try:
        # Create admin user
        user = auth_service.bootstrap_admin(request.username, request.password)
        
        # Generate access token
        access_token = token_service.create_access_token(user)
        
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
        )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with username and password",
    description="Authenticate with username and password to receive an access token.",
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
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
    token_service = TokenService(settings.jwt_secret_key)
    
    # Authenticate user
    user = auth_service.authenticate(request.username, request.password)
    
    if not user:
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    access_token = token_service.create_access_token(user)
    
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
):
    """
    Get current user information.

    Requires valid JWT token in Authorization header.

    Args:
        current_user: Current authenticated user (from JWT token)

    Returns:
        UserResponse: Current user information
    """
    return UserResponse.model_validate(current_user)
