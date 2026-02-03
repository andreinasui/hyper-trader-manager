"""
Authentication router for HyperTrader API.

Handles user registration, login, and API key management.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.config import get_settings
from api.database import get_db
from api.middleware.api_key_auth import get_current_user
from api.middleware.jwt_auth import get_current_user_flexible
from api.models import User
from api.schemas.auth import (
    APIKeyCreate,
    APIKeyResponse,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterResponse,
    UserCreate,
    UserResponse,
)
from api.services.auth_service import AuthService
from api.services.jwt_service import JWTService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Register a new user account with either password or API key authentication. "
        "If password is provided, returns JWT tokens. "
        "If no password, returns API key (backward compatibility). "
        "**Store credentials securely - they will not be shown again.**"
    ),
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
) -> RegisterResponse:
    """
    Register a new user and get authentication credentials.

    - **email**: Valid email address (must be unique)
    - **password**: Optional password for JWT authentication

    Returns user info and either JWT tokens (if password provided) or API key.
    """
    try:
        settings = get_settings()
        user, api_key = AuthService.register_user(
            db,
            user_data.email,
            user_data.password,
        )

        logger.info(f"User registered: {user.email}")

        # Build response based on authentication method
        if user_data.password:
            # JWT-based registration
            access_token = JWTService.create_access_token(user.id, user.email)
            refresh_token = JWTService.create_refresh_token(db, user.id)

            return RegisterResponse(
                user=UserResponse.model_validate(user),
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                message="User registered successfully. Store tokens securely.",
            )
        else:
            # API-key-based registration (backward compatibility)
            return RegisterResponse(
                user=UserResponse.model_validate(user),
                api_key=api_key,
                message="Store this API key securely - it will not be shown again",
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/api-key",
    response_model=APIKeyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate new API key",
    description=(
        "Generate a new API key for the authenticated user. "
        "This invalidates the previous API key. "
        "**Store the new API key securely - it will not be shown again.**"
    ),
)
async def generate_api_key(
    _: APIKeyCreate = None,  # Empty body, just triggers generation
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> APIKeyResponse:
    """
    Generate a new API key for the current user.

    Requires authentication with current valid API key.
    The old API key is invalidated immediately.
    """
    try:
        api_key = AuthService.generate_new_api_key(db, user.id)

        logger.info(f"API key regenerated for user: {user.email}")

        return APIKeyResponse(api_key=api_key)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
    description="Authenticate with email and password to receive JWT tokens.",
)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> LoginResponse:
    """
    Login with email and password.

    - **email**: User's email address
    - **password**: User's password

    Returns JWT access token and refresh token.
    """
    # Authenticate user
    user = AuthService.authenticate_user(db, login_data.email, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    settings = get_settings()
    access_token = JWTService.create_access_token(user.id, user.email)
    refresh_token = JWTService.create_refresh_token(db, user.id)

    logger.info(f"User logged in: {user.email}")

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh access token",
    description="Use a refresh token to get a new access token.",
)
async def refresh(
    refresh_data: RefreshRequest,
    db: Session = Depends(get_db),
) -> RefreshResponse:
    """
    Refresh access token using a refresh token.

    - **refresh_token**: Valid refresh token

    Returns new access token.
    """
    # Verify refresh token
    payload = JWTService.verify_refresh_token(db, refresh_data.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Generate new access token
    settings = get_settings()
    access_token = JWTService.create_access_token(user.id, user.email)

    logger.info(f"Access token refreshed for user: {user.email}")

    return RefreshResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout and revoke refresh token",
    description="Logout by revoking the refresh token.",
)
async def logout(
    refresh_data: RefreshRequest,
    user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Logout by revoking the refresh token.

    - **refresh_token**: Refresh token to revoke

    Returns success message.
    """
    # Revoke the refresh token
    revoked = JWTService.revoke_refresh_token(db, refresh_data.refresh_token)

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found",
        )

    logger.info(f"User logged out: {user.email}")

    return {
        "message": "Successfully logged out",
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_me(
    user: User = Depends(get_current_user_flexible),
) -> UserResponse:
    """
    Get current user information.

    Returns user info without sensitive data (password hash, API key hash).
    """
    return UserResponse.model_validate(user)
