"""
Authentication endpoint tests using mocks.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.database import get_db


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db):
    def override_get_db():
        yield mock_db
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


class TestRegister:
    """Tests for POST /api/v1/auth/register"""

    @patch("api.routers.auth.AuthService.register_user")
    @patch("api.routers.auth.JWTService.create_access_token")
    @patch("api.routers.auth.JWTService.create_refresh_token")
    def test_register_with_password_success(
        self, mock_refresh, mock_access, mock_register, client, mock_db
    ):
        # Setup mocks
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "new@example.com"
        mock_user.plan_tier = "free"
        mock_user.is_admin = False
        mock_user.created_at = datetime.now(timezone.utc)
        
        mock_register.return_value = (mock_user, None)
        mock_access.return_value = "access_token_123"
        mock_refresh.return_value = "refresh_token_123"

        # Make request
        response = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "securepassword123"
        })

        # Assertions
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "new@example.com"
        assert data["access_token"] == "access_token_123"
        assert data["refresh_token"] == "refresh_token_123"
        mock_register.assert_called_once()

    @patch("api.routers.auth.AuthService.register_user")
    def test_register_duplicate_email(self, mock_register, client):
        mock_register.side_effect = ValueError("Email already registered: test@example.com")

        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "password123"
        })

        assert response.status_code == 409
        assert "already registered" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test that invalid email format returns 422."""
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "password123"
        })
        assert response.status_code == 422

    @patch("api.routers.auth.AuthService.register_user")
    def test_register_with_api_key_backward_compatibility(self, mock_register, client):
        """Test registration without password (legacy API key mode)."""
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "legacy@example.com"
        mock_user.plan_tier = "free"
        mock_user.is_admin = False
        mock_user.created_at = datetime.now(timezone.utc)
        
        # Return API key for passwordless registration
        mock_register.return_value = (mock_user, "api_key_12345")

        response = client.post("/api/v1/auth/register", json={
            "email": "legacy@example.com"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "legacy@example.com"
        assert data["api_key"] == "api_key_12345"
        assert data["access_token"] is None
        assert data["refresh_token"] is None


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    @patch("api.routers.auth.AuthService.authenticate_user")
    @patch("api.routers.auth.JWTService.create_access_token")
    @patch("api.routers.auth.JWTService.create_refresh_token")
    def test_login_success(self, mock_refresh, mock_access, mock_auth, client):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "test@example.com"
        mock_user.plan_tier = "free"
        mock_user.is_admin = False
        mock_user.created_at = datetime.now(timezone.utc)
        
        mock_auth.return_value = mock_user
        mock_access.return_value = "access_token_123"
        mock_refresh.return_value = "refresh_token_123"

        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "test@example.com"

    @patch("api.routers.auth.AuthService.authenticate_user")
    def test_login_invalid_credentials(self, mock_auth, client):
        mock_auth.return_value = None

        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    @patch("api.routers.auth.AuthService.authenticate_user")
    def test_login_nonexistent_user(self, mock_auth, client):
        mock_auth.return_value = None

        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "password123"
        })

        assert response.status_code == 401


class TestRefresh:
    """Tests for POST /api/v1/auth/refresh"""

    @patch("api.routers.auth.JWTService.verify_refresh_token")
    @patch("api.routers.auth.JWTService.create_access_token")
    def test_refresh_token_success(self, mock_create, mock_verify, client, mock_db):
        user_id = uuid.uuid4()
        mock_verify.return_value = {"sub": str(user_id), "type": "refresh"}
        mock_create.return_value = "new_access_token"
        
        # Mock the user query
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = "test@example.com"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user

        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "valid_refresh_token"
        })

        assert response.status_code == 200
        assert response.json()["access_token"] == "new_access_token"

    @patch("api.routers.auth.JWTService.verify_refresh_token")
    def test_refresh_token_invalid(self, mock_verify, client):
        mock_verify.return_value = None

        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid_token"
        })

        assert response.status_code == 401

    @patch("api.routers.auth.JWTService.verify_refresh_token")
    def test_refresh_token_user_not_found(self, mock_verify, client, mock_db):
        """Test refresh with valid token but user no longer exists."""
        user_id = uuid.uuid4()
        mock_verify.return_value = {"sub": str(user_id), "type": "refresh"}
        
        # User not found in database
        mock_db.query.return_value.filter.return_value.first.return_value = None

        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "valid_token"
        })

        assert response.status_code == 401


class TestGetMe:
    """Tests for GET /api/v1/auth/me"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    def test_get_me_authenticated(self, mock_get_user, client):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "test@example.com"
        mock_user.plan_tier = "free"
        mock_user.is_admin = False
        mock_user.created_at = datetime.now(timezone.utc)
        
        mock_get_user.return_value = mock_user

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        assert response.json()["email"] == "test@example.com"

    def test_get_me_unauthenticated(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.middleware.jwt_auth.get_current_user_from_api_key")
    def test_get_me_invalid_token(self, mock_api_key, mock_jwt, client):
        """Test that invalid token returns 401."""
        mock_jwt.return_value = None
        mock_api_key.return_value = None
        
        response = client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer invalid.token.here"
        })
        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/v1/auth/logout"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.auth.JWTService.revoke_refresh_token")
    def test_logout_success(self, mock_revoke, mock_get_user, client):
        mock_user = MagicMock()
        mock_user.id = uuid.uuid4()
        mock_user.email = "test@example.com"
        mock_get_user.return_value = mock_user
        mock_revoke.return_value = True

        response = client.post("/api/v1/auth/logout", 
                              headers={"Authorization": "Bearer valid_token"},
                              json={"refresh_token": "refresh_token_123"})

        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.auth.JWTService.revoke_refresh_token")
    def test_logout_invalid_refresh_token(self, mock_revoke, mock_get_user, client):
        mock_user = MagicMock()
        mock_user.email = "test@example.com"
        mock_get_user.return_value = mock_user
        mock_revoke.return_value = False

        response = client.post("/api/v1/auth/logout",
                              headers={"Authorization": "Bearer valid_token"}, 
                              json={"refresh_token": "invalid.token"})

        assert response.status_code == 404
