"""
Tests for TokenService - JWT token creation and verification.

Covers:
- Access token creation
- Token verification
- Token expiration
- Invalid token handling
"""

from datetime import UTC, datetime, timedelta

import pytest

from hyper_trader_api.services.token_service import TokenService


@pytest.fixture
def token_service():
    """Create TokenService with test secret."""
    return TokenService(secret_key="test-secret-key-for-jwt-tokens")


def test_create_access_token(token_service: TokenService, mock_user):
    """Test creating an access token for a user."""
    token = token_service.create_access_token(mock_user)

    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0

    # Token should have 3 parts (header.payload.signature)
    parts = token.split(".")
    assert len(parts) == 3


def test_verify_access_token_valid(token_service: TokenService, mock_user):
    """Test verifying a valid access token."""
    token = token_service.create_access_token(mock_user)
    payload = token_service.verify_access_token(token)

    assert payload is not None
    assert payload["sub"] == mock_user.id
    assert payload["username"] == mock_user.username
    assert payload["is_admin"] == mock_user.is_admin
    assert "exp" in payload
    assert "iat" in payload


def test_verify_access_token_invalid(token_service: TokenService):
    """Test that invalid token returns None."""
    invalid_token = "invalid.token.here"
    payload = token_service.verify_access_token(invalid_token)

    assert payload is None


def test_verify_access_token_wrong_signature(token_service: TokenService, mock_user):
    """Test that token signed with wrong secret is rejected."""
    wrong_service = TokenService(secret_key="different-secret-key")
    token = wrong_service.create_access_token(mock_user)

    payload = token_service.verify_access_token(token)

    assert payload is None


def test_verify_access_token_expired(token_service: TokenService, mock_user):
    """Test that expired token is rejected."""
    # Create token that expires immediately
    token = token_service.create_access_token(mock_user, expires_delta=timedelta(seconds=-1))

    payload = token_service.verify_access_token(token)

    assert payload is None


def test_create_token_with_custom_expiration(token_service: TokenService, mock_user):
    """Test creating token with custom expiration time."""
    expires_delta = timedelta(hours=2)
    token = token_service.create_access_token(mock_user, expires_delta=expires_delta)
    payload = token_service.verify_access_token(token)

    assert payload is not None

    # Check that expiration is approximately 2 hours from now
    exp_time = datetime.fromtimestamp(payload["exp"], tz=UTC)
    now = datetime.now(UTC)
    time_diff = exp_time - now

    # Should be close to 2 hours (within 10 seconds tolerance)
    assert (
        timedelta(hours=2) - timedelta(seconds=10)
        < time_diff
        < timedelta(hours=2) + timedelta(seconds=10)
    )


def test_verify_empty_token(token_service: TokenService):
    """Test that empty token returns None."""
    assert token_service.verify_access_token("") is None


def test_verify_malformed_token(token_service: TokenService):
    """Test that malformed token returns None."""
    malformed_tokens = [
        "not.a.jwt",
        "only-one-part",
        "two.parts",
        "....",
        "header.payload",
    ]

    for token in malformed_tokens:
        assert token_service.verify_access_token(token) is None


def test_token_contains_required_claims(token_service: TokenService, mock_user):
    """Test that token contains all required claims."""
    token = token_service.create_access_token(mock_user)
    payload = token_service.verify_access_token(token)

    assert payload is not None
    required_claims = ["sub", "username", "is_admin", "exp", "iat"]

    for claim in required_claims:
        assert claim in payload, f"Token missing required claim: {claim}"


def test_admin_user_token(token_service: TokenService, mock_admin_user):
    """Test creating and verifying token for admin user."""
    token = token_service.create_access_token(mock_admin_user)
    payload = token_service.verify_access_token(token)

    assert payload is not None
    assert payload["is_admin"] is True
    assert payload["username"] == mock_admin_user.username
