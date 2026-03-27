"""
Tests for SessionTokenService - session token creation, verification, and revocation.

Covers:
- Token creation with correct format and DB storage
- Token verification (valid, expired, revoked, unknown)
- Token revocation
- SHA256 hashing (raw token never stored)
"""

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from hyper_trader_api.services.session_token_service import SessionTokenService


@pytest.fixture
def service(mock_db):
    """Create SessionTokenService with mocked DB session."""
    return SessionTokenService(db=mock_db)


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------


def test_create_session_returns_prefixed_token(service, mock_user):
    """Token returned to caller must start with 'htk_'."""
    token = service.create_session(mock_user)

    assert token.startswith("htk_")


def test_create_session_returns_string(service, mock_user):
    """create_session must return a string."""
    token = service.create_session(mock_user)

    assert isinstance(token, str)


def test_create_session_token_has_sufficient_length(service, mock_user):
    """Token should be long enough to be secure (prefix + 32 bytes urlsafe = ~47 chars)."""
    token = service.create_session(mock_user)

    # "htk_" (4) + secrets.token_urlsafe(32) typically ~43 chars
    assert len(token) >= 40


def test_create_session_stores_hash_not_raw_token(service, mock_user):
    """Raw token must NOT be stored in DB; only its SHA256 hash."""
    token = service.create_session(mock_user)

    # Capture what was added to the DB
    assert service.db.add.called
    stored_obj = service.db.add.call_args[0][0]

    # The stored hash must differ from the raw token
    assert stored_obj.token_hash != token

    # The stored hash must equal SHA256 of the raw token
    expected_hash = hashlib.sha256(token.encode()).hexdigest()
    assert stored_obj.token_hash == expected_hash


def test_create_session_stores_correct_user_id(service, mock_user):
    """Session token must be linked to the correct user."""
    service.create_session(mock_user)

    stored_obj = service.db.add.call_args[0][0]
    assert stored_obj.user_id == mock_user.id


def test_create_session_default_expiry_is_30_days(service, mock_user):
    """Default session expiry must be approximately 30 days from now."""
    now = datetime.now(UTC)
    service.create_session(mock_user)

    stored_obj = service.db.add.call_args[0][0]
    delta = stored_obj.expires_at - now

    # Allow a few seconds of tolerance
    assert timedelta(days=29, hours=23) < delta < timedelta(days=30, hours=1)


def test_create_session_custom_expiry(service, mock_user):
    """create_session must honour a custom expires_days parameter."""
    now = datetime.now(UTC)
    service.create_session(mock_user, expires_days=7)

    stored_obj = service.db.add.call_args[0][0]
    delta = stored_obj.expires_at - now

    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)


def test_create_session_commits_to_db(service, mock_user):
    """Session creation must commit the DB transaction."""
    service.create_session(mock_user)

    service.db.commit.assert_called_once()


def test_create_session_tokens_are_unique(service, mock_user):
    """Each call to create_session must produce a different token."""
    token1 = service.create_session(mock_user)
    token2 = service.create_session(mock_user)

    assert token1 != token2


def test_create_session_is_not_revoked_by_default(service, mock_user):
    """Newly created session must not be revoked."""
    service.create_session(mock_user)

    stored_obj = service.db.add.call_args[0][0]
    assert stored_obj.is_revoked is False


# ---------------------------------------------------------------------------
# verify_session
# ---------------------------------------------------------------------------


def _make_session_token(user_id: str, token: str, *, revoked: bool = False, expired: bool = False, naive_tz: bool = False):
    """Helper: build a mock SessionToken ORM object."""
    session = MagicMock()
    session.user_id = user_id
    session.token_hash = hashlib.sha256(token.encode()).hexdigest()
    session.is_revoked = revoked
    if expired:
        if naive_tz:
            session.expires_at = datetime.utcnow() - timedelta(hours=1)
        else:
            session.expires_at = datetime.now(UTC) - timedelta(hours=1)
    else:
        if naive_tz:
            session.expires_at = datetime.utcnow() + timedelta(days=30)
        else:
            session.expires_at = datetime.now(UTC) + timedelta(days=30)
    return session


def test_verify_session_valid_token_returns_user_id(service, mock_user, mock_db):
    """verify_session with a valid token must return the user_id."""
    token = "htk_validtoken123"
    mock_session = _make_session_token(mock_user.id, token)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    result = service.verify_session(token)

    assert result == mock_user.id


def test_verify_session_unknown_token_returns_none(service, mock_db):
    """verify_session for a token not in DB must return None."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = service.verify_session("htk_unknowntoken")

    assert result is None


def test_verify_session_revoked_token_returns_none(service, mock_user, mock_db):
    """verify_session for a revoked token must return None."""
    token = "htk_revokedtoken"
    mock_session = _make_session_token(mock_user.id, token, revoked=True)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    result = service.verify_session(token)

    assert result is None


def test_verify_session_expired_token_returns_none(service, mock_user, mock_db):
    """verify_session for an expired token must return None."""
    token = "htk_expiredtoken"
    mock_session = _make_session_token(mock_user.id, token, expired=True)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    result = service.verify_session(token)

    assert result is None


def test_verify_session_looks_up_by_hash(service, mock_db):
    """verify_session must hash the token and use that hash for the DB lookup."""
    token = "htk_sometoken"
    expected_hash = hashlib.sha256(token.encode()).hexdigest()

    mock_db.query.return_value.filter.return_value.first.return_value = None

    captured_hashes: list[str] = []

    original_hash = hashlib.sha256

    def capturing_sha256(data):
        digest = original_hash(data)
        if isinstance(data, (bytes, bytearray)):
            captured_hashes.append(digest.hexdigest())
        return digest

    with patch("hashlib.sha256", side_effect=capturing_sha256):
        service.verify_session(token)

    # The expected hash must have been computed during verify_session
    assert expected_hash in captured_hashes


def test_verify_session_empty_token_returns_none(service):
    """verify_session with empty string must return None without hitting DB."""
    result = service.verify_session("")

    assert result is None


def test_verify_session_handles_timezone_naive_expires_at(service, mock_user, mock_db):
    """verify_session must handle timezone-naive expires_at from SQLite."""
    token = "htk_naivetoken"
    # SQLite returns timezone-naive datetimes; simulate this
    mock_session = _make_session_token(mock_user.id, token, naive_tz=True)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    result = service.verify_session(token)

    # Should succeed - the service normalizes naive datetimes to UTC
    assert result == mock_user.id


# ---------------------------------------------------------------------------
# revoke_session
# ---------------------------------------------------------------------------


def test_revoke_session_marks_token_as_revoked(service, mock_user, mock_db):
    """revoke_session must set is_revoked=True on the matching session."""
    token = "htk_activetoken"
    mock_session = _make_session_token(mock_user.id, token)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    service.revoke_session(token)

    assert mock_session.is_revoked is True


def test_revoke_session_returns_true_on_success(service, mock_user, mock_db):
    """revoke_session must return True when a session is found and revoked."""
    token = "htk_activetoken"
    mock_session = _make_session_token(mock_user.id, token)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    result = service.revoke_session(token)

    assert result is True


def test_revoke_session_returns_false_when_not_found(service, mock_db):
    """revoke_session must return False when token is not found in DB."""
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = service.revoke_session("htk_nosuchtoken")

    assert result is False


def test_revoke_session_commits_to_db(service, mock_user, mock_db):
    """revoke_session must commit after marking the token revoked."""
    token = "htk_tokentorevoke"
    mock_session = _make_session_token(mock_user.id, token)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    service.revoke_session(token)

    mock_db.commit.assert_called_once()


def test_revoke_session_empty_token_returns_false(service):
    """revoke_session with empty string must return False without hitting DB."""
    result = service.revoke_session("")

    assert result is False
