# Session Token Migration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace JWT authentication with stateful session tokens for simpler auth and real logout capability.

**Architecture:** Random prefixed tokens (`htk_...`) stored in DB, looked up on each request. 30-day expiration with server-side revocation.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite

---

## Summary of Changes

| Component | Action |
|-----------|--------|
| `SessionToken` model | Already exists - no changes needed |
| `SessionTokenService` | Create: new service for token management |
| `session_auth.py` | Create: new middleware replacing jwt_auth |
| `auth.py` router | Update: use session tokens, add logout endpoint |
| `config.py` | Remove `jwt_secret_key` |
| `token_service.py` | Delete: JWT service no longer needed |
| `jwt_auth.py` | Delete: replaced by session_auth |
| `pyproject.toml` | Remove `PyJWT` dependency |
| Frontend `useAuth.tsx` | Update: add logout API call |
| Tests | Update all auth tests |

---

### Task 1: Create Session Token Service

**Files:**
- Create: `api/hyper_trader_api/services/session_token_service.py`
- Test: `api/tests/test_session_token_service.py`

**Step 1: Write the failing test**

```python
# api/tests/test_session_token_service.py
"""Tests for SessionTokenService."""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from hyper_trader_api.services.session_token_service import SessionTokenService


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def service(mock_db):
    """Create service with mock db."""
    return SessionTokenService(mock_db)


def test_create_session_returns_prefixed_token(service, mock_user):
    """Test that created token has htk_ prefix."""
    token = service.create_session(mock_user)
    
    assert token.startswith("htk_")
    assert len(token) > 40  # htk_ + at least 32 chars


def test_create_session_stores_hashed_token(service, mock_user, mock_db):
    """Test that session is stored with hashed token."""
    token = service.create_session(mock_user)
    
    # Verify add was called
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    
    # Get the SessionToken that was added
    session_token = mock_db.add.call_args[0][0]
    
    # Hash should NOT equal the raw token
    assert session_token.token_hash != token
    assert session_token.user_id == mock_user.id
    assert session_token.is_revoked is False


def test_verify_session_valid_token(service, mock_user, mock_db):
    """Test verifying a valid session token."""
    # Create a real token first
    token = service.create_session(mock_user)
    
    # Mock the query to return the session
    mock_session = MagicMock()
    mock_session.user_id = mock_user.id
    mock_session.is_revoked = False
    mock_session.expires_at = datetime.now(UTC) + timedelta(days=1)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_session
    
    user_id = service.verify_session(token)
    
    assert user_id == mock_user.id


def test_verify_session_expired_token(service, mock_db):
    """Test that expired token returns None."""
    mock_session = MagicMock()
    mock_session.is_revoked = False
    mock_session.expires_at = datetime.now(UTC) - timedelta(days=1)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_session
    
    user_id = service.verify_session("htk_sometoken")
    
    assert user_id is None


def test_verify_session_revoked_token(service, mock_db):
    """Test that revoked token returns None."""
    mock_session = MagicMock()
    mock_session.is_revoked = True
    mock_session.expires_at = datetime.now(UTC) + timedelta(days=1)
    mock_db.query.return_value.filter.return_value.first.return_value = mock_session
    
    user_id = service.verify_session("htk_sometoken")
    
    assert user_id is None


def test_verify_session_not_found(service, mock_db):
    """Test that unknown token returns None."""
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    user_id = service.verify_session("htk_unknown")
    
    assert user_id is None


def test_revoke_session(service, mock_db):
    """Test revoking a session."""
    mock_session = MagicMock()
    mock_session.is_revoked = False
    mock_db.query.return_value.filter.return_value.first.return_value = mock_session
    
    result = service.revoke_session("htk_sometoken")
    
    assert result is True
    assert mock_session.is_revoked is True
    mock_db.commit.assert_called_once()


def test_revoke_session_not_found(service, mock_db):
    """Test revoking non-existent session returns False."""
    mock_db.query.return_value.filter.return_value.first.return_value = None
    
    result = service.revoke_session("htk_unknown")
    
    assert result is False
```

**Step 2: Run test to verify it fails**

Run: `cd api && uv run pytest tests/test_session_token_service.py -v`
Expected: FAIL with "No module named 'hyper_trader_api.services.session_token_service'"

**Step 3: Write minimal implementation**

```python
# api/hyper_trader_api/services/session_token_service.py
"""
Session token service for stateful authentication.

Creates, verifies, and revokes session tokens stored in the database.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from hyper_trader_api.models.session_token import SessionToken
from hyper_trader_api.models.user import User


class SessionTokenService:
    """
    Service for session token management.
    
    Tokens are prefixed with 'htk_' for identification.
    Only hashes are stored in the database.
    """
    
    TOKEN_PREFIX = "htk_"
    DEFAULT_EXPIRY_DAYS = 30
    
    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
    
    def _generate_token(self) -> str:
        """Generate a secure random token with prefix."""
        random_bytes = secrets.token_urlsafe(32)
        return f"{self.TOKEN_PREFIX}{random_bytes}"
    
    def _hash_token(self, token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
    
    def create_session(
        self,
        user: User,
        expires_days: int | None = None,
    ) -> str:
        """
        Create a new session token for a user.
        
        Args:
            user: User to create session for
            expires_days: Days until expiration (default: 30)
            
        Returns:
            Raw token string (only returned once, not stored)
        """
        if expires_days is None:
            expires_days = self.DEFAULT_EXPIRY_DAYS
            
        token = self._generate_token()
        token_hash = self._hash_token(token)
        expires_at = datetime.now(UTC) + timedelta(days=expires_days)
        
        session_token = SessionToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            is_revoked=False,
        )
        
        self.db.add(session_token)
        self.db.commit()
        
        return token
    
    def verify_session(self, token: str) -> str | None:
        """
        Verify a session token and return the user ID.
        
        Args:
            token: Raw token string from client
            
        Returns:
            User ID if valid, None otherwise
        """
        if not token or not token.startswith(self.TOKEN_PREFIX):
            return None
            
        token_hash = self._hash_token(token)
        
        session = (
            self.db.query(SessionToken)
            .filter(SessionToken.token_hash == token_hash)
            .first()
        )
        
        if not session:
            return None
            
        if session.is_revoked:
            return None
            
        if session.expires_at < datetime.now(UTC):
            return None
            
        return session.user_id
    
    def revoke_session(self, token: str) -> bool:
        """
        Revoke a session token.
        
        Args:
            token: Raw token string
            
        Returns:
            True if revoked, False if not found
        """
        if not token:
            return False
            
        token_hash = self._hash_token(token)
        
        session = (
            self.db.query(SessionToken)
            .filter(SessionToken.token_hash == token_hash)
            .first()
        )
        
        if not session:
            return False
            
        session.is_revoked = True
        self.db.commit()
        
        return True
```

**Step 4: Run test to verify it passes**

Run: `cd api && uv run pytest tests/test_session_token_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/hyper_trader_api/services/session_token_service.py api/tests/test_session_token_service.py
git commit -m "feat(auth): add session token service for stateful auth"
```

---

### Task 2: Create Session Auth Middleware

**Files:**
- Create: `api/hyper_trader_api/middleware/session_auth.py`
- Test: `api/tests/test_session_auth.py`

**Step 1: Write the failing test**

```python
# api/tests/test_session_auth.py
"""Tests for session authentication middleware."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


def test_get_current_user_missing_header():
    """Test that missing auth header raises 401."""
    from hyper_trader_api.middleware.session_auth import get_current_user
    
    request = MagicMock()
    request.headers.get.return_value = None
    db = MagicMock()
    
    with pytest.raises(HTTPException) as exc_info:
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            get_current_user(request, db)
        )
    
    assert exc_info.value.status_code == 401


def test_get_current_user_invalid_token():
    """Test that invalid token raises 401."""
    from hyper_trader_api.middleware.session_auth import get_current_user
    
    request = MagicMock()
    request.headers.get.return_value = "Bearer htk_invalid"
    db = MagicMock()
    
    with patch('hyper_trader_api.middleware.session_auth.SessionTokenService') as MockService:
        MockService.return_value.verify_session.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                get_current_user(request, db)
            )
        
        assert exc_info.value.status_code == 401


def test_get_current_user_valid_token(mock_user):
    """Test that valid token returns user."""
    from hyper_trader_api.middleware.session_auth import get_current_user
    
    request = MagicMock()
    request.headers.get.return_value = "Bearer htk_validtoken"
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = mock_user
    
    with patch('hyper_trader_api.middleware.session_auth.SessionTokenService') as MockService:
        MockService.return_value.verify_session.return_value = mock_user.id
        
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            get_current_user(request, db)
        )
        
        assert result == mock_user
```

**Step 2: Run test to verify it fails**

Run: `cd api && uv run pytest tests/test_session_auth.py -v`
Expected: FAIL with "No module named 'hyper_trader_api.middleware.session_auth'"

**Step 3: Write minimal implementation**

```python
# api/hyper_trader_api/middleware/session_auth.py
"""
Session-based authentication middleware for HyperTrader API.

Validates session tokens stored in the database.
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
    Authenticate user using session token.
    
    Extracts Bearer token from Authorization header, verifies it
    against the database, and retrieves the user.
    
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
    
    # Verify token
    token_service = SessionTokenService(db)
    user_id = token_service.verify_session(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Look up user
    user = db.query(User).filter_by(id=user_id).first()
    
    if not user:
        logger.warning(f"User not found for session: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.debug(f"User authenticated: {user.username}")
    return user
```

**Step 4: Run test to verify it passes**

Run: `cd api && uv run pytest tests/test_session_auth.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add api/hyper_trader_api/middleware/session_auth.py api/tests/test_session_auth.py
git commit -m "feat(auth): add session-based auth middleware"
```

---

### Task 3: Update Auth Router

**Files:**
- Modify: `api/hyper_trader_api/routers/auth.py`

**Step 1: Update imports and add logout endpoint**

Replace the entire file with:

```python
# api/hyper_trader_api/routers/auth.py
"""
Authentication router for HyperTrader API.

Local username/password authentication with session tokens.
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
    """Check if system is initialized."""
    auth_service = LocalAuthService(db)
    initialized = auth_service.system_initialized()
    return SetupStatusResponse(initialized=initialized)


@router.post(
    "/bootstrap",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bootstrap the first admin user",
    description="Create the first admin user during initial system setup.",
)
async def bootstrap_admin(
    request: BootstrapRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Bootstrap the system with the first admin user."""
    auth_service = LocalAuthService(db)
    token_service = SessionTokenService(db)

    try:
        user = auth_service.bootstrap_admin(request.username, request.password)
        access_token = token_service.create_session(user)

        logger.info(f"System bootstrapped with admin user: {user.username}")

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )

    except ValueError as e:
        logger.warning(f"Bootstrap attempt failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with username and password",
    description="Authenticate with username and password to receive a session token.",
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> AuthResponse:
    """Authenticate user with username and password."""
    auth_service = LocalAuthService(db)
    token_service = SessionTokenService(db)

    user = auth_service.authenticate(request.username, request.password)

    if not user:
        logger.warning(f"Failed login attempt for username: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = token_service.create_session(user)

    logger.info(f"User logged in: {user.username}")

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


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
    token = auth_header.replace("Bearer ", "")
    
    token_service = SessionTokenService(db)
    token_service.revoke_session(token)
    
    logger.info(f"User logged out: {current_user.username}")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)
```

**Step 2: Run existing auth tests**

Run: `cd api && uv run pytest tests/test_auth.py -v`
Expected: Tests should still pass (may need minor updates)

**Step 3: Commit**

```bash
git add api/hyper_trader_api/routers/auth.py
git commit -m "feat(auth): switch auth router to session tokens, add logout"
```

---

### Task 4: Update Router Imports

**Files:**
- Modify: `api/hyper_trader_api/routers/traders.py` (and any other routers using jwt_auth)

**Step 1: Find and update imports**

Search for `from hyper_trader_api.middleware.jwt_auth import get_current_user` and replace with:
`from hyper_trader_api.middleware.session_auth import get_current_user`

**Step 2: Run tests**

Run: `cd api && uv run pytest tests/test_traders.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add api/hyper_trader_api/routers/
git commit -m "refactor(auth): update routers to use session auth"
```

---

### Task 5: Remove JWT Dependencies

**Files:**
- Delete: `api/hyper_trader_api/services/token_service.py`
- Delete: `api/hyper_trader_api/middleware/jwt_auth.py`
- Delete: `api/tests/test_token_service.py`
- Delete: `api/tests/test_jwt_service.py` (if exists)
- Modify: `api/hyper_trader_api/config.py` (remove jwt_secret_key)
- Modify: `api/pyproject.toml` (remove PyJWT)

**Step 1: Delete old JWT files**

```bash
rm api/hyper_trader_api/services/token_service.py
rm api/hyper_trader_api/middleware/jwt_auth.py
rm api/tests/test_token_service.py
rm -f api/tests/test_jwt_service.py
```

**Step 2: Update config.py**

Remove these lines from `api/hyper_trader_api/config.py`:

```python
# Remove this line from Settings class:
jwt_secret_key: str = "dev-secret-key-change-in-production"

# Update the validator - change from:
@field_validator("jwt_secret_key", "encryption_key")
# To:
@field_validator("encryption_key")
```

**Step 3: Remove PyJWT from dependencies**

Edit `api/pyproject.toml`, remove `PyJWT` from dependencies list.

**Step 4: Update lockfile**

Run: `cd api && uv lock`

**Step 5: Run all tests**

Run: `cd api && uv run pytest -v`
Expected: PASS (some tests may need updating)

**Step 6: Commit**

```bash
git add -A
git commit -m "chore(auth): remove JWT dependencies and config"
```

---

### Task 6: Update Frontend Logout

**Files:**
- Modify: `web/src/hooks/useAuth.tsx`

**Step 1: Add logout API call**

Update the `logout` function in `useAuth.tsx`:

```typescript
const logout = useCallback(async () => {
  const token = localStorage.getItem('auth_token')
  
  // Revoke session on server
  if (token) {
    try {
      await fetch(`${config.VITE_API_URL}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
    } catch (error) {
      // Ignore errors - we're logging out anyway
      console.warn('Logout request failed:', error)
    }
  }
  
  localStorage.removeItem('auth_token')
  setState(s => ({
    ...s,
    token: null,
    user: null,
    authenticated: false,
  }))
}, [])
```

**Step 2: Run frontend type check**

Run: `cd web && pnpm tsc --noEmit`
Expected: No errors

**Step 3: Commit**

```bash
git add web/src/hooks/useAuth.tsx
git commit -m "feat(web): add server-side logout"
```

---

### Task 7: Update Tests

**Files:**
- Modify: `api/tests/conftest.py`
- Modify: `api/tests/test_auth.py` (if needed)

**Step 1: Update conftest.py**

Update `auth_headers` fixture:

```python
@pytest.fixture
def auth_headers():
    """Authorization headers with mock session token."""
    return {"Authorization": "Bearer htk_mock_session_token"}


@pytest.fixture
def mock_session_token():
    """Mock session token."""
    return "htk_mock_session_token"
```

**Step 2: Update test_auth.py if needed**

Review and update any tests that reference JWT-specific behavior.

**Step 3: Run all tests**

Run: `cd api && uv run pytest -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add api/tests/
git commit -m "test(auth): update tests for session token auth"
```

---

### Task 8: Final Verification

**Step 1: Run full test suite**

```bash
cd api && uv run pytest -v
cd ../web && pnpm tsc --noEmit
```

**Step 2: Manual test**

1. Start API: `cd api && uv run uvicorn hyper_trader_api.main:app --reload`
2. Start web: `cd web && pnpm dev`
3. Test login flow
4. Test logout (verify token is revoked - re-using old token should fail)
5. Test protected routes

**Step 3: Final commit**

```bash
git add -A
git commit -m "feat(auth): complete migration to session tokens"
```

---

## Rollback Plan

If issues arise, the migration can be reverted by:
1. `git revert <commit-hashes>` for each commit
2. Restoring `token_service.py` and `jwt_auth.py` from git history
3. Re-adding `PyJWT` to dependencies
