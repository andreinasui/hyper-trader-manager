"""
Tests for LocalAuthService - local username/password authentication.

Covers:
- Bootstrap admin creation (only once)
- System initialization check
- Username/password authentication
"""

import pytest
from sqlalchemy.orm import Session

from hyper_trader_api.models.user import User
from hyper_trader_api.services.local_auth_service import LocalAuthService


def test_system_not_initialized_when_no_users(mock_db: Session):
    """Test that system is not initialized when no users exist."""
    mock_db.query.return_value.first.return_value = None
    service = LocalAuthService(mock_db)
    assert service.system_initialized() is False


def test_system_initialized_when_users_exist(mock_db: Session, mock_user):
    """Test that system is initialized when any user exists."""
    mock_db.query.return_value.first.return_value = mock_user
    service = LocalAuthService(mock_db)
    assert service.system_initialized() is True


def test_bootstrap_admin_creates_admin_user(mock_db: Session):
    """Test that bootstrap_admin creates an admin user when system is not initialized."""
    mock_db.query.return_value.first.return_value = None
    mock_db.add.return_value = None
    mock_db.commit.return_value = None

    service = LocalAuthService(mock_db)
    user = service.bootstrap_admin("admin", "secret123")

    assert user is not None
    assert user.username == "admin"
    assert user.is_admin is True
    assert user.password_hash is not None
    assert user.password_hash != "secret123"  # Should be hashed

    # Verify db operations were called
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_bootstrap_admin_fails_when_system_initialized(mock_db: Session, mock_user):
    """Test that bootstrap_admin fails when any user already exists."""
    mock_db.query.return_value.first.return_value = mock_user

    service = LocalAuthService(mock_db)

    with pytest.raises(ValueError, match="already initialized"):
        service.bootstrap_admin("admin", "secret123")


def test_bootstrap_admin_validates_username(mock_db: Session):
    """Test that bootstrap_admin validates username."""
    mock_db.query.return_value.first.return_value = None

    service = LocalAuthService(mock_db)

    with pytest.raises(ValueError, match="Username"):
        service.bootstrap_admin("", "secret123")

    with pytest.raises(ValueError, match="Username"):
        service.bootstrap_admin("ab", "secret123")  # Too short


def test_bootstrap_admin_validates_password(mock_db: Session):
    """Test that bootstrap_admin validates password strength."""
    mock_db.query.return_value.first.return_value = None

    service = LocalAuthService(mock_db)

    with pytest.raises(ValueError, match="Password"):
        service.bootstrap_admin("admin", "")

    with pytest.raises(ValueError, match="Password"):
        service.bootstrap_admin("admin", "short")  # Too short


def test_authenticate_success(mock_db: Session):
    """Test successful authentication with correct credentials."""
    from hyper_trader_api.utils.crypto import hash_password

    # Create a user with hashed password
    mock_user = User(
        username="testuser",
        password_hash=hash_password("correct_password"),
        is_admin=False,
    )

    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    service = LocalAuthService(mock_db)
    user = service.authenticate("testuser", "correct_password")

    assert user is not None
    assert user.username == "testuser"


def test_authenticate_wrong_password(mock_db: Session):
    """Test authentication fails with incorrect password."""
    from hyper_trader_api.utils.crypto import hash_password

    mock_user = User(
        username="testuser",
        password_hash=hash_password("correct_password"),
        is_admin=False,
    )

    mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

    service = LocalAuthService(mock_db)
    user = service.authenticate("testuser", "wrong_password")

    assert user is None


def test_authenticate_nonexistent_user(mock_db: Session):
    """Test authentication fails for nonexistent user."""
    mock_db.query.return_value.filter_by.return_value.first.return_value = None

    service = LocalAuthService(mock_db)
    user = service.authenticate("nonexistent", "password")

    assert user is None


def test_authenticate_validates_input(mock_db: Session):
    """Test that authenticate validates input parameters."""
    service = LocalAuthService(mock_db)

    # Empty username
    assert service.authenticate("", "password") is None

    # Empty password
    assert service.authenticate("username", "") is None
