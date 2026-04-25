"""
Authentication endpoint tests for local auth.

Tests for username/password authentication with session tokens:
- GET /api/v1/auth/setup-status
- POST /api/v1/auth/bootstrap
- POST /api/v1/auth/login
- GET /api/v1/auth/me
- POST /api/v1/auth/logout
"""

from unittest.mock import patch


class TestSetupStatus:
    """Tests for GET /api/v1/auth/setup-status"""

    def test_setup_status_returns_uninitialized(self, client, mock_db):
        """Test setup-status returns initialized=False when no users exist."""
        # Mock LocalAuthService to return False for system_initialized
        with patch("hyper_trader_api.routers.auth.LocalAuthService") as MockAuth:
            mock_auth = MockAuth.return_value
            mock_auth.system_initialized.return_value = False

            response = client.get("/api/v1/auth/setup-status")

            assert response.status_code == 200
            assert response.json() == {"initialized": False}

    def test_setup_status_returns_initialized(self, client, mock_db):
        """Test setup-status returns initialized=True when users exist."""
        with patch("hyper_trader_api.routers.auth.LocalAuthService") as MockAuth:
            mock_auth = MockAuth.return_value
            mock_auth.system_initialized.return_value = True

            response = client.get("/api/v1/auth/setup-status")

            assert response.status_code == 200
            assert response.json() == {"initialized": True}


class TestBootstrap:
    """Tests for POST /api/v1/auth/bootstrap"""

    def test_bootstrap_creates_admin_user(self, client, mock_db, mock_admin_user):
        """Test bootstrap creates first admin user and returns session token."""
        with (
            patch("hyper_trader_api.routers.auth.LocalAuthService") as MockAuth,
            patch("hyper_trader_api.routers.auth.SessionTokenService") as MockToken,
        ):
            mock_auth = MockAuth.return_value
            mock_auth.bootstrap_admin.return_value = mock_admin_user

            mock_token_service = MockToken.return_value
            mock_token_service.create_session.return_value = "htk_test_session_token"

            response = client.post(
                "/api/v1/auth/bootstrap",
                json={"username": "admin", "password": "securepassword123"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["access_token"] == "htk_test_session_token"
            assert data["token_type"] == "bearer"
            assert data["user"]["username"] == "admin"
            assert data["user"]["is_admin"] is True

    def test_bootstrap_uses_session_token_service(self, client, mock_db, mock_admin_user):
        """Test bootstrap calls SessionTokenService.create_session (not JWT)."""
        with (
            patch("hyper_trader_api.routers.auth.LocalAuthService") as MockAuth,
            patch("hyper_trader_api.routers.auth.SessionTokenService") as MockToken,
        ):
            mock_auth = MockAuth.return_value
            mock_auth.bootstrap_admin.return_value = mock_admin_user

            mock_token_service = MockToken.return_value
            mock_token_service.create_session.return_value = "htk_session_token"

            client.post(
                "/api/v1/auth/bootstrap",
                json={"username": "admin", "password": "securepassword123"},
            )

            # Ensure SessionTokenService was constructed with the db
            MockToken.assert_called_once_with(mock_db)
            # Ensure create_session was called (not create_access_token from JWT)
            mock_token_service.create_session.assert_called_once_with(mock_admin_user)

    def test_bootstrap_rejects_when_already_initialized(self, client, mock_db):
        """Test bootstrap fails if system is already initialized."""
        with patch("hyper_trader_api.routers.auth.LocalAuthService") as MockAuth:
            mock_auth = MockAuth.return_value
            mock_auth.bootstrap_admin.side_effect = ValueError("System already initialized")

            response = client.post(
                "/api/v1/auth/bootstrap",
                json={"username": "admin", "password": "securepassword123"},
            )

            assert response.status_code == 409
            assert "already initialized" in response.json()["detail"].lower()

    def test_bootstrap_validates_username_length(self, client, mock_db):
        """Test bootstrap rejects username shorter than 3 characters."""
        response = client.post(
            "/api/v1/auth/bootstrap", json={"username": "ab", "password": "securepassword123"}
        )

        assert response.status_code == 422

    def test_bootstrap_validates_password_length(self, client, mock_db):
        """Test bootstrap rejects password shorter than 8 characters."""
        response = client.post(
            "/api/v1/auth/bootstrap", json={"username": "admin", "password": "short"}
        )

        assert response.status_code == 422


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    def test_login_with_valid_credentials(self, client, mock_db, mock_user):
        """Test login succeeds with valid username and password."""
        with (
            patch("hyper_trader_api.routers.auth.LocalAuthService") as MockAuth,
            patch("hyper_trader_api.routers.auth.SessionTokenService") as MockToken,
        ):
            mock_auth = MockAuth.return_value
            mock_auth.authenticate.return_value = mock_user

            mock_token_service = MockToken.return_value
            mock_token_service.create_session.return_value = "htk_test_session_token"

            response = client.post(
                "/api/v1/auth/login", json={"username": "testuser", "password": "password123"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "htk_test_session_token"
            assert data["token_type"] == "bearer"
            assert data["user"]["username"] == "testuser"

    def test_login_uses_session_token_service(self, client, mock_db, mock_user):
        """Test login calls SessionTokenService.create_session (not JWT)."""
        with (
            patch("hyper_trader_api.routers.auth.LocalAuthService") as MockAuth,
            patch("hyper_trader_api.routers.auth.SessionTokenService") as MockToken,
        ):
            mock_auth = MockAuth.return_value
            mock_auth.authenticate.return_value = mock_user

            mock_token_service = MockToken.return_value
            mock_token_service.create_session.return_value = "htk_session_token"

            client.post(
                "/api/v1/auth/login", json={"username": "testuser", "password": "password123"}
            )

            # Ensure SessionTokenService was constructed with the db
            MockToken.assert_called_once_with(mock_db)
            # Ensure create_session was called (not create_access_token from JWT)
            mock_token_service.create_session.assert_called_once_with(mock_user)

    def test_login_with_invalid_credentials(self, client, mock_db):
        """Test login fails with invalid credentials."""
        with patch("hyper_trader_api.routers.auth.LocalAuthService") as MockAuth:
            mock_auth = MockAuth.return_value
            mock_auth.authenticate.return_value = None

            response = client.post(
                "/api/v1/auth/login", json={"username": "testuser", "password": "wrongpassword"}
            )

            assert response.status_code == 401
            assert "invalid credentials" in response.json()["detail"].lower()

    def test_login_requires_username(self, client, mock_db):
        """Test login requires username field."""
        response = client.post("/api/v1/auth/login", json={"password": "password123"})

        assert response.status_code == 422

    def test_login_requires_password(self, client, mock_db):
        """Test login requires password field."""
        response = client.post("/api/v1/auth/login", json={"username": "testuser"})

        assert response.status_code == 422


class TestGetMe:
    """Tests for GET /api/v1/auth/me"""

    def test_get_me_authenticated(self, client, mock_db, mock_user):
        """Test /me returns current user info when authenticated with session token."""
        with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockToken:
            mock_token_service = MockToken.return_value
            mock_token_service.verify_session.return_value = mock_user.id

            # Mock database query to return user
            mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

            response = client.get(
                "/api/v1/auth/me", headers={"Authorization": "Bearer htk_valid_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == mock_user.id
            assert data["username"] == mock_user.username
            assert data["is_admin"] == mock_user.is_admin
            assert "created_at" in data

    def test_get_me_missing_auth_header(self, client, mock_db):
        """Test /me returns 401 when Authorization header is missing."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower()

    def test_get_me_invalid_token(self, client, mock_db):
        """Test /me returns 401 when token is invalid."""
        with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockToken:
            mock_token_service = MockToken.return_value
            mock_token_service.verify_session.return_value = None

            response = client.get(
                "/api/v1/auth/me", headers={"Authorization": "Bearer htk_invalid_token"}
            )

            assert response.status_code == 401
            assert "invalid" in response.json()["detail"].lower()

    def test_get_me_expired_token(self, client, mock_db):
        """Test /me returns 401 when token is expired."""
        with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockToken:
            mock_token_service = MockToken.return_value
            mock_token_service.verify_session.return_value = None

            response = client.get(
                "/api/v1/auth/me", headers={"Authorization": "Bearer htk_expired_token"}
            )

            assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/v1/auth/logout"""

    def test_logout_revokes_session_token(self, client, mock_db, mock_user):
        """Test logout revokes the session token and returns 204."""
        with (
            patch(
                "hyper_trader_api.middleware.session_auth.SessionTokenService"
            ) as MockSessionAuth,
            patch("hyper_trader_api.routers.auth.SessionTokenService") as MockTokenRevoke,
        ):
            # Auth middleware verifies token successfully
            mock_session_auth = MockSessionAuth.return_value
            mock_session_auth.verify_session.return_value = mock_user.id
            mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

            # Router's SessionTokenService for revocation
            mock_revoke_service = MockTokenRevoke.return_value
            mock_revoke_service.revoke_session.return_value = True

            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer htk_valid_token"},
            )

            assert response.status_code == 204

    def test_logout_calls_revoke_session_with_token(self, client, mock_db, mock_user):
        """Test logout extracts the Bearer token and calls revoke_session with it."""
        with (
            patch(
                "hyper_trader_api.middleware.session_auth.SessionTokenService"
            ) as MockSessionAuth,
            patch("hyper_trader_api.routers.auth.SessionTokenService") as MockTokenRevoke,
        ):
            mock_session_auth = MockSessionAuth.return_value
            mock_session_auth.verify_session.return_value = mock_user.id
            mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user

            mock_revoke_service = MockTokenRevoke.return_value
            mock_revoke_service.revoke_session.return_value = True

            client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer htk_specific_token"},
            )

            # Verify revoke_session was called with just the token (no "Bearer " prefix)
            mock_revoke_service.revoke_session.assert_called_once_with("htk_specific_token")

    def test_logout_requires_authentication(self, client, mock_db):
        """Test logout returns 401 when no Authorization header is provided."""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == 401

    def test_logout_rejects_invalid_token(self, client, mock_db):
        """Test logout returns 401 when session token is invalid."""
        with patch("hyper_trader_api.middleware.session_auth.SessionTokenService") as MockToken:
            mock_token_service = MockToken.return_value
            mock_token_service.verify_session.return_value = None

            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": "Bearer htk_invalid_token"},
            )

            assert response.status_code == 401
