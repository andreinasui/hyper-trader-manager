"""
JWT Service unit tests using mocks.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from hyper_trader_api.services.jwt_service import JWTService


class TestCreateAccessToken:
    """Tests for JWTService.create_access_token"""

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_creates_valid_token(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"
        mock_settings.return_value.jwt_access_token_expire_minutes = 15

        user_id = uuid.uuid4()
        token = JWTService.create_access_token(user_id, "test@example.com")

        assert isinstance(token, str)
        assert len(token) > 0

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_token_can_be_verified(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"
        mock_settings.return_value.jwt_access_token_expire_minutes = 15

        user_id = uuid.uuid4()
        token = JWTService.create_access_token(user_id, "test@example.com")
        payload = JWTService.verify_access_token(token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_token_contains_expiration(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"
        mock_settings.return_value.jwt_access_token_expire_minutes = 15

        user_id = uuid.uuid4()
        token = JWTService.create_access_token(user_id, "test@example.com")
        payload = JWTService.verify_access_token(token)

        assert "exp" in payload
        assert "iat" in payload


class TestVerifyAccessToken:
    """Tests for JWTService.verify_access_token"""

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_invalid_token_returns_none(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"

        payload = JWTService.verify_access_token("invalid_token")
        assert payload is None

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_wrong_secret_returns_none(self, mock_settings):
        # Create token with one secret
        mock_settings.return_value.jwt_secret_key = "secret1"
        mock_settings.return_value.jwt_algorithm = "HS256"
        mock_settings.return_value.jwt_access_token_expire_minutes = 15

        token = JWTService.create_access_token(uuid.uuid4(), "test@example.com")

        # Try to verify with different secret
        mock_settings.return_value.jwt_secret_key = "secret2"
        payload = JWTService.verify_access_token(token)

        assert payload is None

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_empty_token_returns_none(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"

        payload = JWTService.verify_access_token("")
        assert payload is None


class TestCreateRefreshToken:
    """Tests for JWTService.create_refresh_token"""

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_creates_token_and_stores_hash(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"
        mock_settings.return_value.jwt_refresh_token_expire_days = 7

        mock_db = MagicMock()
        user_id = uuid.uuid4()

        token = JWTService.create_refresh_token(mock_db, user_id)

        assert isinstance(token, str)
        assert len(token) > 0
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_token_includes_jti(self, mock_settings):
        """Test that refresh token includes a unique token ID."""
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"
        mock_settings.return_value.jwt_refresh_token_expire_days = 7

        mock_db = MagicMock()
        user_id = uuid.uuid4()

        token = JWTService.create_refresh_token(mock_db, user_id)

        # Verify token structure (decode without validation for testing)
        from jose import jwt

        payload = jwt.decode(
            token,
            mock_settings.return_value.jwt_secret_key,
            algorithms=[mock_settings.return_value.jwt_algorithm],
        )

        assert "jti" in payload
        assert payload["type"] == "refresh"


class TestVerifyRefreshToken:
    """Tests for JWTService.verify_refresh_token"""

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_valid_token_returns_payload(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"
        mock_settings.return_value.jwt_refresh_token_expire_days = 7

        mock_db = MagicMock()
        user_id = uuid.uuid4()

        # Create a token
        token = JWTService.create_refresh_token(mock_db, user_id)

        # Mock the database query to return a non-revoked token
        mock_token = MagicMock()
        mock_token.revoked = False
        mock_token.expires_at = datetime.now(UTC) + timedelta(days=7)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_token

        # Verify the token
        payload = JWTService.verify_refresh_token(mock_db, token)

        assert payload is not None
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_revoked_token_returns_none(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"
        mock_settings.return_value.jwt_refresh_token_expire_days = 7

        mock_db = MagicMock()

        # Mock the database query to return None (revoked or not found)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        payload = JWTService.verify_refresh_token(mock_db, "some_token")

        assert payload is None

    @patch("hyper_trader_api.services.jwt_service.get_settings")
    def test_invalid_token_returns_none(self, mock_settings):
        mock_settings.return_value.jwt_secret_key = "test_secret"
        mock_settings.return_value.jwt_algorithm = "HS256"

        mock_db = MagicMock()
        payload = JWTService.verify_refresh_token(mock_db, "invalid_token")

        assert payload is None


class TestRevokeRefreshToken:
    """Tests for JWTService.revoke_refresh_token"""

    def test_revoke_existing_token(self):
        mock_db = MagicMock()
        mock_token = MagicMock()
        mock_token.revoked = False
        mock_db.query.return_value.filter.return_value.first.return_value = mock_token

        result = JWTService.revoke_refresh_token(mock_db, "some_token")

        assert result is True
        assert mock_token.revoked is True
        mock_db.commit.assert_called_once()

    def test_revoke_nonexistent_token(self):
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = JWTService.revoke_refresh_token(mock_db, "nonexistent_token")

        assert result is False
        mock_db.commit.assert_not_called()


class TestRevokeAllUserTokens:
    """Tests for JWTService.revoke_all_user_tokens"""

    def test_revokes_multiple_tokens(self):
        mock_db = MagicMock()
        user_id = uuid.uuid4()

        # Mock the update to return count of 3
        mock_db.query.return_value.filter.return_value.update.return_value = 3

        count = JWTService.revoke_all_user_tokens(mock_db, user_id)

        assert count == 3
        mock_db.commit.assert_called_once()

    def test_revokes_zero_tokens_when_none_exist(self):
        mock_db = MagicMock()
        user_id = uuid.uuid4()

        # Mock the update to return count of 0
        mock_db.query.return_value.filter.return_value.update.return_value = 0

        count = JWTService.revoke_all_user_tokens(mock_db, user_id)

        assert count == 0


class TestCleanupExpiredTokens:
    """Tests for JWTService.cleanup_expired_tokens"""

    def test_deletes_expired_tokens(self):
        mock_db = MagicMock()

        # Mock delete to return count of 5
        mock_db.query.return_value.filter.return_value.delete.return_value = 5

        count = JWTService.cleanup_expired_tokens(mock_db)

        assert count == 5
        mock_db.commit.assert_called_once()

    def test_deletes_zero_when_none_expired(self):
        mock_db = MagicMock()

        # Mock delete to return count of 0
        mock_db.query.return_value.filter.return_value.delete.return_value = 0

        count = JWTService.cleanup_expired_tokens(mock_db)

        assert count == 0
