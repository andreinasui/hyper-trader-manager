"""
Tests for SSLSetupService.

Covers:
- SSLSetupService.get_ssl_config: fetches the singleton SSLConfig
- SSLSetupService.is_ssl_configured: checks if SSL has been set up
- SSLSetupService.configure_domain_ssl: Let's Encrypt setup flow
- SSLSetupService._restart_traefik: Docker container restart
- SSLSetupService._save_config: database persistence
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hyper_trader_api.services.ssl_setup_service import SSLSetupError, SSLSetupService


class TestSSLSetupError:
    """Tests for SSLSetupError exception class."""

    def test_is_exception(self):
        """SSLSetupError is a subclass of Exception."""
        err = SSLSetupError("something went wrong")
        assert isinstance(err, Exception)
        assert str(err) == "something went wrong"

    def test_can_be_raised(self):
        """SSLSetupError can be raised and caught."""
        with pytest.raises(SSLSetupError, match="test error"):
            raise SSLSetupError("test error")


class TestSSLSetupServiceInit:
    """Tests for SSLSetupService initialization."""

    def test_init_stores_db_session(self):
        """SSLSetupService stores the database session."""
        mock_db = MagicMock()
        service = SSLSetupService(mock_db)
        assert service.db is mock_db


class TestGetSslConfig:
    """Tests for get_ssl_config method."""

    def test_returns_none_when_no_config_exists(self):
        """get_ssl_config returns None when no SSLConfig row exists."""
        mock_db = MagicMock()
        mock_db.get.return_value = None

        service = SSLSetupService(mock_db)
        result = service.get_ssl_config()

        assert result is None

    def test_returns_config_when_exists(self):
        """get_ssl_config returns the SSLConfig object when it exists."""
        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.mode = "domain"
        mock_config.domain = "example.com"
        mock_db.get.return_value = mock_config

        service = SSLSetupService(mock_db)
        result = service.get_ssl_config()

        assert result is mock_config

    def test_queries_ssl_config_with_id_1(self):
        """get_ssl_config queries SSLConfig with id=1 (singleton pattern)."""
        from hyper_trader_api.models.ssl_config import SSLConfig

        mock_db = MagicMock()
        service = SSLSetupService(mock_db)
        service.get_ssl_config()

        mock_db.get.assert_called_once_with(SSLConfig, 1)


class TestIsSslConfigured:
    """Tests for is_ssl_configured method."""

    def test_returns_false_when_no_config(self):
        """is_ssl_configured returns False when no config exists."""
        mock_db = MagicMock()
        mock_db.get.return_value = None

        service = SSLSetupService(mock_db)
        assert service.is_ssl_configured() is False

    def test_returns_false_when_config_has_no_mode(self):
        """is_ssl_configured returns False when config.mode is None."""
        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.mode = None
        mock_db.get.return_value = mock_config

        service = SSLSetupService(mock_db)
        assert service.is_ssl_configured() is False

    def test_returns_true_when_domain_mode(self):
        """is_ssl_configured returns True when mode is 'domain'."""
        mock_db = MagicMock()
        mock_config = MagicMock()
        mock_config.mode = "domain"
        mock_db.get.return_value = mock_config

        service = SSLSetupService(mock_db)
        assert service.is_ssl_configured() is True


class TestRestartTraefik:
    """Tests for _restart_traefik private method."""

    def test_connects_to_docker_and_restarts_container(self):
        """_restart_traefik gets the hypertrader-traefik container and calls restart."""
        mock_db = MagicMock()
        mock_container = MagicMock()
        mock_docker_client = MagicMock()
        mock_docker_client.containers.get.return_value = mock_container

        service = SSLSetupService(mock_db)
        with patch("docker.from_env", return_value=mock_docker_client):
            service._restart_traefik()

        mock_docker_client.containers.get.assert_called_once_with("hypertrader-traefik")
        mock_container.restart.assert_called_once_with(timeout=30)

    def test_raises_ssl_setup_error_when_container_not_found(self):
        """_restart_traefik raises SSLSetupError when container is not found."""
        import docker.errors

        mock_db = MagicMock()
        mock_docker_client = MagicMock()
        mock_docker_client.containers.get.side_effect = docker.errors.NotFound(
            "Container not found"
        )

        service = SSLSetupService(mock_db)
        with patch("docker.from_env", return_value=mock_docker_client):
            with pytest.raises(SSLSetupError, match="Traefik container not found"):
                service._restart_traefik()

    def test_raises_ssl_setup_error_on_docker_api_error(self):
        """_restart_traefik raises SSLSetupError on Docker API errors."""
        import docker.errors

        mock_db = MagicMock()
        mock_docker_client = MagicMock()
        mock_docker_client.containers.get.side_effect = docker.errors.APIError("Docker error")

        service = SSLSetupService(mock_db)
        with patch("docker.from_env", return_value=mock_docker_client):
            with pytest.raises(SSLSetupError, match="Failed to restart Traefik"):
                service._restart_traefik()


class TestSaveConfig:
    """Tests for _save_config private method."""

    def test_creates_new_config_when_none_exists(self):
        """_save_config creates SSLConfig(id=1) when no config exists."""
        from hyper_trader_api.models.ssl_config import SSLConfig

        mock_db = MagicMock()
        mock_db.get.return_value = None

        service = SSLSetupService(mock_db)
        service._save_config(mode="domain", domain="example.com", email="admin@example.com")

        # Should have added a new object
        mock_db.add.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert isinstance(added_obj, SSLConfig)
        assert added_obj.id == 1
        assert added_obj.mode == "domain"
        assert added_obj.domain == "example.com"
        assert added_obj.email == "admin@example.com"
        mock_db.commit.assert_called_once()

    def test_updates_existing_config(self):
        """_save_config updates existing SSLConfig when one already exists."""
        from hyper_trader_api.models.ssl_config import SSLConfig

        mock_db = MagicMock()
        existing_config = SSLConfig(id=1, mode="ip_only", domain=None, email=None)
        mock_db.get.return_value = existing_config

        service = SSLSetupService(mock_db)
        service._save_config(mode="domain", domain="example.com", email="admin@example.com")

        # Should NOT add a new object, just modify existing
        mock_db.add.assert_not_called()
        assert existing_config.mode == "domain"
        assert existing_config.domain == "example.com"
        assert existing_config.email == "admin@example.com"
        mock_db.commit.assert_called_once()

    def test_sets_configured_at_timestamp(self):
        """_save_config sets configured_at to current datetime."""
        from datetime import UTC, datetime

        mock_db = MagicMock()
        mock_db.get.return_value = None

        service = SSLSetupService(mock_db)
        before = datetime.now(UTC)
        service._save_config(mode="domain", domain="example.com", email="admin@example.com")
        after = datetime.now(UTC)

        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.configured_at is not None
        assert before <= added_obj.configured_at <= after


class TestConfigureDomainSsl:
    """Tests for configure_domain_ssl method."""

    def _make_service_with_mocks(self, tmp_path: Path):
        """Create service with common mocks for domain SSL tests."""
        mock_db = MagicMock()
        mock_db.get.return_value = None  # No existing config
        service = SSLSetupService(mock_db)
        return service, mock_db

    def test_returns_https_url(self, tmp_path: Path):
        """configure_domain_ssl returns https://domain redirect URL."""
        service, mock_db = self._make_service_with_mocks(tmp_path)

        with (
            patch("hyper_trader_api.services.ssl_setup_service.get_settings") as mock_settings,
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
            patch("docker.from_env") as mock_docker,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "production"
            mock_settings_obj.traefik_config_dir = str(tmp_path)
            mock_settings.return_value = mock_settings_obj
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer
            mock_writer.backup_config.return_value = None
            mock_container = MagicMock()
            mock_docker.return_value.containers.get.return_value = mock_container

            result = service.configure_domain_ssl("example.com", "admin@example.com")

        assert result == "https://example.com"

    def test_writes_domain_traefik_config(self, tmp_path: Path):
        """configure_domain_ssl calls TraefikConfigWriter.write_domain_config."""
        service, mock_db = self._make_service_with_mocks(tmp_path)

        with (
            patch("hyper_trader_api.services.ssl_setup_service.get_settings") as mock_settings,
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
            patch("docker.from_env") as mock_docker,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "production"
            mock_settings_obj.traefik_config_dir = str(tmp_path)
            mock_settings.return_value = mock_settings_obj
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer
            mock_writer.backup_config.return_value = None
            mock_container = MagicMock()
            mock_docker.return_value.containers.get.return_value = mock_container

            service.configure_domain_ssl("example.com", "admin@example.com")

        mock_writer.write_domain_config.assert_called_once_with("example.com", "admin@example.com")

    def test_restarts_traefik_container(self, tmp_path: Path):
        """configure_domain_ssl restarts the Traefik container."""
        service, mock_db = self._make_service_with_mocks(tmp_path)

        with (
            patch("hyper_trader_api.services.ssl_setup_service.get_settings") as mock_settings,
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
            patch("docker.from_env") as mock_docker,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "production"
            mock_settings_obj.traefik_config_dir = str(tmp_path)
            mock_settings.return_value = mock_settings_obj
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer
            mock_writer.backup_config.return_value = None
            mock_docker_client = MagicMock()
            mock_container = MagicMock()
            mock_docker.return_value = mock_docker_client
            mock_docker_client.containers.get.return_value = mock_container

            service.configure_domain_ssl("example.com", "admin@example.com")

        mock_container.restart.assert_called_once_with(timeout=30)

    def test_saves_config_to_database(self, tmp_path: Path):
        """configure_domain_ssl saves domain config to the database."""
        service, mock_db = self._make_service_with_mocks(tmp_path)

        with (
            patch("hyper_trader_api.services.ssl_setup_service.get_settings") as mock_settings,
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
            patch("docker.from_env") as mock_docker,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "production"
            mock_settings_obj.traefik_config_dir = str(tmp_path)
            mock_settings.return_value = mock_settings_obj
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer
            mock_writer.backup_config.return_value = None
            mock_docker.return_value.containers.get.return_value = MagicMock()

            service.configure_domain_ssl("example.com", "admin@example.com")

        mock_db.commit.assert_called_once()
        added_obj = mock_db.add.call_args[0][0]
        assert added_obj.mode == "domain"
        assert added_obj.domain == "example.com"
        assert added_obj.email == "admin@example.com"

    def test_restores_backup_and_raises_on_config_write_failure(self, tmp_path: Path):
        """configure_domain_ssl restores backup and raises SSLSetupError on config write failure."""
        from hyper_trader_api.services.traefik_config import TraefikConfigError

        service, mock_db = self._make_service_with_mocks(tmp_path)

        with (
            patch("hyper_trader_api.services.ssl_setup_service.get_settings") as mock_settings,
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "production"
            mock_settings_obj.traefik_config_dir = str(tmp_path)
            mock_settings.return_value = mock_settings_obj
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer
            backup = ("traefik: original\n", "http:\n  routers: {}\n")
            mock_writer.backup_config.return_value = backup
            mock_writer.write_domain_config.side_effect = TraefikConfigError("write failed")

            with pytest.raises(SSLSetupError):
                service.configure_domain_ssl("example.com", "admin@example.com")

        mock_writer.restore_config.assert_called_once_with(backup)

    def test_restores_backup_and_raises_on_traefik_restart_failure(self, tmp_path: Path):
        """configure_domain_ssl restores backup and raises SSLSetupError on restart failure."""
        service, mock_db = self._make_service_with_mocks(tmp_path)

        with (
            patch("hyper_trader_api.services.ssl_setup_service.get_settings") as mock_settings,
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
            patch("docker.from_env") as mock_docker,
        ):
            mock_settings_obj = MagicMock()
            mock_settings_obj.environment = "production"
            mock_settings_obj.traefik_config_dir = str(tmp_path)
            mock_settings.return_value = mock_settings_obj
            mock_writer = MagicMock()
            mock_writer_cls.return_value = mock_writer
            backup = ("traefik: original\n", "http:\n  routers: {}\n")
            mock_writer.backup_config.return_value = backup
            mock_docker_client = MagicMock()
            mock_docker.return_value = mock_docker_client
            mock_docker_client.containers.get.side_effect = SSLSetupError(
                "Traefik container not found"
            )

            with pytest.raises(SSLSetupError):
                service.configure_domain_ssl("example.com", "admin@example.com")

        mock_writer.restore_config.assert_called_once_with(backup)

    def test_configure_domain_ssl_rejects_non_production_environment(self):
        """configure_domain_ssl raises SSLSetupError when environment is not production."""
        mock_db = MagicMock()
        mock_db.get.return_value = None
        service = SSLSetupService(mock_db)

        mock_settings = MagicMock()
        mock_settings.environment = "development"

        with patch(
            "hyper_trader_api.services.ssl_setup_service.get_settings", return_value=mock_settings
        ):
            with pytest.raises(SSLSetupError, match="SSL setup is only available in production"):
                service.configure_domain_ssl("example.com", "admin@example.com")
