"""
SSL setup router endpoint tests.

Tests for:
- GET /api/v1/setup/ssl-status
- POST /api/v1/setup/ssl
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_production_env():
    """Mock settings to simulate production environment."""
    mock_settings = MagicMock()
    mock_settings.environment = "production"
    with patch("hyper_trader_api.routers.ssl_setup.get_settings", return_value=mock_settings):
        yield mock_settings


class TestSSLStatus:
    """Tests for GET /api/v1/setup/ssl-status"""

    def test_ssl_status_returns_not_configured(self, client, mock_db, mock_production_env):
        """Test ssl-status returns ssl_configured=False when SSL is not configured."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_ssl_config.return_value = None

            response = client.get("/api/v1/setup/ssl-status")

            assert response.status_code == 200
            data = response.json()
            assert data["ssl_configured"] is False
            assert data["mode"] is None
            assert data["domain"] is None
            assert data["configured_at"] is None

    def test_ssl_status_returns_domain_mode(self, client, mock_db, mock_production_env):
        """Test ssl-status returns domain mode details when SSL is configured."""
        configured_at = datetime(2026, 3, 27, 12, 0, 0, tzinfo=UTC)
        mock_config = MagicMock()
        mock_config.mode = "domain"
        mock_config.domain = "trader.example.com"
        mock_config.configured_at = configured_at

        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_ssl_config.return_value = mock_config

            response = client.get("/api/v1/setup/ssl-status")

            assert response.status_code == 200
            data = response.json()
            assert data["ssl_configured"] is True
            assert data["mode"] == "domain"
            assert data["domain"] == "trader.example.com"
            assert data["configured_at"] is not None

    def test_ssl_status_constructs_service_with_db(self, client, mock_db, mock_production_env):
        """Test ssl-status constructs SSLSetupService with the database session."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_ssl_config.return_value = None

            client.get("/api/v1/setup/ssl-status")

            MockService.assert_called_once_with(mock_db)

    def test_ssl_status_returns_configured_in_development_mode(self, client, mock_db):
        """Test ssl-status always returns ssl_configured=True in development mode."""
        mock_settings = MagicMock()
        mock_settings.environment = "development"
        with patch("hyper_trader_api.routers.ssl_setup.get_settings", return_value=mock_settings):
            response = client.get("/api/v1/setup/ssl-status")

            assert response.status_code == 200
            data = response.json()
            assert data["ssl_configured"] is True
            assert data["mode"] == "domain"

    def test_ssl_status_no_auth_required(self, client, mock_db, mock_production_env):
        """Test ssl-status is accessible without authentication."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.get_ssl_config.return_value = None

            # No Authorization header
            response = client.get("/api/v1/setup/ssl-status")

            assert response.status_code == 200


class TestSSLSetup:
    """Tests for POST /api/v1/setup/ssl"""

    def test_configure_domain_ssl_success(self, client, mock_db, mock_production_env):
        """Test POST /ssl configures domain SSL and returns redirect URL."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False
            mock_service.configure_domain_ssl.return_value = "https://trader.example.com"

            response = client.post(
                "/api/v1/setup/ssl",
                json={
                    "mode": "domain",
                    "domain": "trader.example.com",
                    "email": "admin@example.com",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["redirect_url"] == "https://trader.example.com"

    def test_configure_domain_ssl_calls_service_correctly(
        self, client, mock_db, mock_production_env
    ):
        """Test POST /ssl calls configure_domain_ssl with domain and email."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False
            mock_service.configure_domain_ssl.return_value = "https://trader.example.com"

            client.post(
                "/api/v1/setup/ssl",
                json={
                    "mode": "domain",
                    "domain": "trader.example.com",
                    "email": "admin@example.com",
                },
            )

            mock_service.configure_domain_ssl.assert_called_once_with(
                domain="trader.example.com", email="admin@example.com"
            )

    def test_returns_400_if_already_configured(self, client, mock_db, mock_production_env):
        """Test POST /ssl returns 400 if SSL is already configured."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = True

            response = client.post(
                "/api/v1/setup/ssl",
                json={"mode": "domain", "domain": "example.com", "email": "admin@example.com"},
            )

            assert response.status_code == 400
            assert "already" in response.json()["detail"].lower()

    def test_returns_422_if_domain_is_missing(self, client, mock_db, mock_production_env):
        """Test POST /ssl returns 422 if domain is missing (Pydantic validation)."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False

            response = client.post(
                "/api/v1/setup/ssl",
                json={"mode": "domain", "email": "admin@example.com"},
            )

            assert response.status_code == 422

    def test_returns_422_if_email_is_missing(self, client, mock_db, mock_production_env):
        """Test POST /ssl returns 422 if email is missing (Pydantic validation)."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False

            response = client.post(
                "/api/v1/setup/ssl",
                json={"mode": "domain", "domain": "trader.example.com"},
            )

            assert response.status_code == 422

    def test_returns_500_on_ssl_setup_error(self, client, mock_db, mock_production_env):
        """Test POST /ssl returns 500 when SSLSetupError is raised."""
        from hyper_trader_api.services.ssl_setup_service import SSLSetupError

        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False
            mock_service.configure_domain_ssl.side_effect = SSLSetupError("Docker failure")

            response = client.post(
                "/api/v1/setup/ssl",
                json={
                    "mode": "domain",
                    "domain": "trader.example.com",
                    "email": "admin@example.com",
                },
            )

            assert response.status_code == 500
            assert "Docker failure" in response.json()["detail"]

    def test_no_auth_required(self, client, mock_db, mock_production_env):
        """Test POST /ssl is accessible without authentication (first-time setup)."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False
            mock_service.configure_domain_ssl.return_value = "https://trader.example.com"

            # No Authorization header
            response = client.post(
                "/api/v1/setup/ssl",
                json={
                    "mode": "domain",
                    "domain": "trader.example.com",
                    "email": "admin@example.com",
                },
            )

            assert response.status_code == 200

    def test_constructs_service_with_db(self, client, mock_db, mock_production_env):
        """Test POST /ssl constructs SSLSetupService with the database session."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False
            mock_service.configure_domain_ssl.return_value = "https://trader.example.com"

            client.post(
                "/api/v1/setup/ssl",
                json={
                    "mode": "domain",
                    "domain": "trader.example.com",
                    "email": "admin@example.com",
                },
            )

            MockService.assert_called_once_with(mock_db)

    def test_domain_ssl_message_in_response(self, client, mock_db, mock_production_env):
        """Test POST /ssl domain mode includes a message in the response."""
        with patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService:
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False
            mock_service.configure_domain_ssl.return_value = "https://trader.example.com"

            response = client.post(
                "/api/v1/setup/ssl",
                json={
                    "mode": "domain",
                    "domain": "trader.example.com",
                    "email": "admin@example.com",
                },
            )

            data = response.json()
            assert "message" in data
            assert isinstance(data["message"], str)
            assert len(data["message"]) > 0


class TestSSLSetupRouterEnvironmentGate:
    """Tests for production environment gate on SSL setup endpoints"""

    def test_post_ssl_returns_403_in_development(self, client, mock_db):
        """Test POST /ssl returns 403 in development environment."""
        mock_settings = MagicMock()
        mock_settings.environment = "development"

        with patch("hyper_trader_api.routers.ssl_setup.get_settings", return_value=mock_settings):
            response = client.post(
                "/api/v1/setup/ssl",
                json={
                    "mode": "domain",
                    "domain": "example.com",
                    "email": "admin@example.com",
                },
            )

            assert response.status_code == 403
            assert "production" in response.json()["detail"].lower()

    def test_post_ssl_proceeds_in_production(self, client, mock_db):
        """Test POST /ssl proceeds when in production environment."""
        mock_settings = MagicMock()
        mock_settings.environment = "production"

        with (
            patch("hyper_trader_api.routers.ssl_setup.get_settings", return_value=mock_settings),
            patch("hyper_trader_api.routers.ssl_setup.SSLSetupService") as MockService,
        ):
            mock_service = MockService.return_value
            mock_service.is_ssl_configured.return_value = False
            mock_service.configure_domain_ssl.return_value = "https://example.com"

            response = client.post(
                "/api/v1/setup/ssl",
                json={
                    "mode": "domain",
                    "domain": "example.com",
                    "email": "admin@example.com",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
