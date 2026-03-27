"""
Tests for session_auth middleware.

Covers:
- Valid Bearer token returns the User from DB
- Missing Authorization header raises 401
- Malformed/non-Bearer Authorization header raises 401
- Invalid or expired token (SessionTokenService returns None) raises 401
- User not found in DB raises 401
- 401 responses include WWW-Authenticate: Bearer header
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(auth_header: str | None = None) -> MagicMock:
    """Build a mock FastAPI Request with the given Authorization header value."""
    request = MagicMock()
    headers: dict[str, str] = {}
    if auth_header is not None:
        headers["Authorization"] = auth_header
    request.headers = headers
    return request


# ---------------------------------------------------------------------------
# get_current_user – happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_returns_user_for_valid_token(mock_db, mock_user):
    """Valid Bearer token should return the User from the database."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    token = "htk_validtoken123"
    request = _make_request(f"Bearer {token}")

    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockService:
        mock_service = MockService.return_value
        mock_service.verify_session.return_value = mock_user.id

        result = await get_current_user(request=request, db=mock_db)

    assert result is mock_user


@pytest.mark.asyncio
async def test_get_current_user_passes_token_to_verify_session(mock_db, mock_user):
    """The raw token extracted from the header must be forwarded to verify_session."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    token = "htk_sometesttoken"
    request = _make_request(f"Bearer {token}")

    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockService:
        mock_service = MockService.return_value
        mock_service.verify_session.return_value = mock_user.id

        await get_current_user(request=request, db=mock_db)

        mock_service.verify_session.assert_called_once_with(token)


@pytest.mark.asyncio
async def test_get_current_user_queries_db_with_user_id(mock_db, mock_user):
    """After verify_session returns user_id, DB must be queried for that user."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    token = "htk_sometoken"
    user_id = str(uuid.uuid4())
    request = _make_request(f"Bearer {token}")

    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockService:
        mock_service = MockService.return_value
        mock_service.verify_session.return_value = user_id

        await get_current_user(request=request, db=mock_db)

    mock_db.query.return_value.filter_by.assert_called_once_with(id=user_id)


# ---------------------------------------------------------------------------
# get_current_user – missing / malformed Authorization header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_no_auth_header(mock_db):
    """Missing Authorization header must raise HTTP 401."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    request = _make_request(auth_header=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_for_empty_auth_header(mock_db):
    """Empty Authorization header must raise HTTP 401."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    request = _make_request(auth_header="")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_raises_401_for_non_bearer_scheme(mock_db):
    """Authorization header with non-Bearer scheme must raise HTTP 401."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    request = _make_request(auth_header="Basic dXNlcjpwYXNz")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_401_includes_www_authenticate_header_for_missing_auth(
    mock_db,
):
    """401 for missing auth header must include WWW-Authenticate: Bearer."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    request = _make_request(auth_header=None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, db=mock_db)

    assert exc_info.value.headers is not None
    assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"


# ---------------------------------------------------------------------------
# get_current_user – invalid / expired token
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_verify_session_returns_none(mock_db):
    """When SessionTokenService.verify_session returns None, raise HTTP 401."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    token = "htk_badtoken"
    request = _make_request(f"Bearer {token}")

    with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockService:
        mock_service = MockService.return_value
        mock_service.verify_session.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=request, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_401_includes_www_authenticate_header_for_invalid_token(
    mock_db,
):
    """401 for invalid token must include WWW-Authenticate: Bearer."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    token = "htk_expiredtoken"
    request = _make_request(f"Bearer {token}")

    with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockService:
        mock_service = MockService.return_value
        mock_service.verify_session.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=request, db=mock_db)

    assert exc_info.value.headers is not None
    assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"


# ---------------------------------------------------------------------------
# get_current_user – user not found in DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_user_raises_401_when_user_not_in_db(mock_db):
    """When verify_session returns a user_id but User not in DB, raise HTTP 401."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    token = "htk_orphantoken"
    user_id = str(uuid.uuid4())
    request = _make_request(f"Bearer {token}")

    # Simulate DB returning no user
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockService:
        mock_service = MockService.return_value
        mock_service.verify_session.return_value = user_id

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=request, db=mock_db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_401_includes_www_authenticate_header_for_missing_user(
    mock_db,
):
    """401 for user-not-found must include WWW-Authenticate: Bearer."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    token = "htk_orphantoken2"
    user_id = str(uuid.uuid4())
    request = _make_request(f"Bearer {token}")

    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockService:
        mock_service = MockService.return_value
        mock_service.verify_session.return_value = user_id

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request=request, db=mock_db)

    assert exc_info.value.headers is not None
    assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"
