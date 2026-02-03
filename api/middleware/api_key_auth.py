"""
API Key authentication middleware for HyperTrader API.

Extracts and validates API keys from request headers.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.config import get_settings
from api.database import get_db
from api.models import User
from api.services.auth_service import AuthService


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate API key from request, return authenticated user.

    This function should be used as a FastAPI dependency:

        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}

    Args:
        request: FastAPI Request object
        db: Database session (injected by FastAPI)

    Returns:
        User: Authenticated user

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    settings = get_settings()
    api_key_header = settings.api_key_header  # Default: X-API-Key

    # Extract API key from header
    api_key = request.headers.get(api_key_header)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing {api_key_header} header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate API key
    user = AuthService.get_user_by_api_key(db, api_key)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return user
