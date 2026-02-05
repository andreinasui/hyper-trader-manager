"""
Auth Service unit tests using mocks.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from hyper_trader_api.services.auth_service import AuthService


class TestRegisterUser:
    """Tests for AuthService.register_user"""

    def test_register_with_password(self):
        """Test registering a user with password."""
        mock_db = MagicMock()

        # Mock the query to return None (no existing user)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("hyper_trader_api.services.auth_service.hash_password") as mock_hash:
            mock_hash.return_value = "hashed_password"

            user, api_key = AuthService.register_user(mock_db, "test@example.com", "password123")

            # Should create user with password hash
            assert api_key is None
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_hash.assert_called_once_with("password123")

    def test_register_without_password(self):
        """Test registering a user without password (API key mode)."""
        mock_db = MagicMock()

        # Mock the query to return None (no existing user)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with (
            patch("hyper_trader_api.services.auth_service.generate_api_key") as mock_gen,
            patch("hyper_trader_api.services.auth_service.hash_api_key") as mock_hash,
        ):
            mock_gen.return_value = "api_key_123"
            mock_hash.return_value = "hashed_api_key"

            user, api_key = AuthService.register_user(mock_db, "test@example.com", None)

            # Should create user with API key
            assert api_key == "api_key_123"
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

    def test_register_duplicate_email(self):
        """Test that duplicate email raises ValueError."""
        mock_db = MagicMock()

        # Mock existing user
        existing_user = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        with pytest.raises(ValueError, match="Email already registered"):
            AuthService.register_user(mock_db, "existing@example.com", "password123")


class TestAuthenticateUser:
    """Tests for AuthService.authenticate_user"""

    def test_authenticate_success(self):
        """Test successful authentication."""
        mock_db = MagicMock()

        # Mock user with password hash
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_hash = "hashed_password"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch("hyper_trader_api.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = True

            result = AuthService.authenticate_user(mock_db, "test@example.com", "correct_password")

            assert result == mock_user
            mock_verify.assert_called_once_with("correct_password", "hashed_password")

    def test_authenticate_wrong_password(self):
        """Test authentication with wrong password."""
        mock_db = MagicMock()

        # Mock user with password hash
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_hash = "hashed_password"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with patch("hyper_trader_api.services.auth_service.verify_password") as mock_verify:
            mock_verify.return_value = False

            result = AuthService.authenticate_user(mock_db, "test@example.com", "wrong_password")

            assert result is None

    def test_authenticate_user_not_found(self):
        """Test authentication when user doesn't exist."""
        mock_db = MagicMock()

        # Mock no user found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = AuthService.authenticate_user(mock_db, "nonexistent@example.com", "password")

        assert result is None

    def test_authenticate_user_no_password_hash(self):
        """Test authentication when user has no password (API key only)."""
        mock_db = MagicMock()

        # Mock user without password hash
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_user.password_hash = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        result = AuthService.authenticate_user(mock_db, "test@example.com", "password")

        assert result is None


class TestGenerateNewApiKey:
    """Tests for AuthService.generate_new_api_key"""

    def test_generate_new_api_key_success(self):
        """Test generating new API key for existing user."""
        mock_db = MagicMock()
        user_id = uuid.uuid4()

        # Mock user
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        with (
            patch("hyper_trader_api.services.auth_service.generate_api_key") as mock_gen,
            patch("hyper_trader_api.services.auth_service.hash_api_key") as mock_hash,
        ):
            mock_gen.return_value = "new_api_key_123"
            mock_hash.return_value = "hashed_new_api_key"

            api_key = AuthService.generate_new_api_key(mock_db, user_id)

            assert api_key == "new_api_key_123"
            assert mock_user.api_key_hash == "hashed_new_api_key"
            mock_db.commit.assert_called_once()

    def test_generate_new_api_key_user_not_found(self):
        """Test generating API key for non-existent user."""
        mock_db = MagicMock()
        user_id = uuid.uuid4()

        # Mock no user found
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="User not found"):
            AuthService.generate_new_api_key(mock_db, user_id)


class TestGetUserByApiKey:
    """Tests for AuthService.get_user_by_api_key"""

    def test_get_user_by_valid_api_key(self):
        """Test getting user with valid API key."""
        mock_db = MagicMock()

        # Mock users
        mock_user1 = MagicMock()
        mock_user1.api_key_hash = "hash1"
        mock_user2 = MagicMock()
        mock_user2.api_key_hash = "hash2"

        mock_db.query.return_value.all.return_value = [mock_user1, mock_user2]

        with patch("hyper_trader_api.services.auth_service.verify_api_key") as mock_verify:
            # First call returns False, second returns True
            mock_verify.side_effect = [False, True]

            result = AuthService.get_user_by_api_key(mock_db, "valid_api_key")

            assert result == mock_user2

    def test_get_user_by_invalid_api_key(self):
        """Test getting user with invalid API key."""
        mock_db = MagicMock()

        # Mock users
        mock_user1 = MagicMock()
        mock_user1.api_key_hash = "hash1"
        mock_user2 = MagicMock()
        mock_user2.api_key_hash = "hash2"

        mock_db.query.return_value.all.return_value = [mock_user1, mock_user2]

        with patch("hyper_trader_api.services.auth_service.verify_api_key") as mock_verify:
            # All calls return False (no match)
            mock_verify.return_value = False

            result = AuthService.get_user_by_api_key(mock_db, "invalid_api_key")

            assert result is None

    def test_get_user_by_api_key_no_users(self):
        """Test getting user when no users exist."""
        mock_db = MagicMock()

        # Mock empty user list
        mock_db.query.return_value.all.return_value = []

        result = AuthService.get_user_by_api_key(mock_db, "any_key")

        assert result is None
