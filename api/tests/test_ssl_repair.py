"""
Tests for SSLSetupService.repair_if_inconsistent().

Covers the startup consistency check that detects stale ssl_config DB rows
(SSL marked configured but traefik.yml lacks ACME config) and auto-repairs
by re-writing Traefik config files and restarting Traefik.
"""

import logging
from unittest.mock import MagicMock, patch

from hyper_trader_api.services.ssl_setup_service import SSLSetupService


def _make_ssl_config(mode="domain", domain="example.com", email="admin@example.com"):
    """Return a mock SSLConfig with sensible defaults."""
    cfg = MagicMock()
    cfg.mode = mode
    cfg.domain = domain
    cfg.email = email
    return cfg


def _make_settings(
    environment="production", traefik_config_dir="/host-traefik", acme_ca_server=None
):
    """Return a mock settings object."""
    s = MagicMock()
    s.environment = environment
    s.traefik_config_dir = traefik_config_dir
    s.acme_ca_server = acme_ca_server
    return s


class TestRepairIfInconsistent:
    """Tests for SSLSetupService.repair_if_inconsistent()."""

    def _service(self, ssl_config_return):
        """Build a service whose get_ssl_config returns the given value."""
        mock_db = MagicMock()
        mock_db.get.return_value = ssl_config_return
        return SSLSetupService(mock_db)

    # ------------------------------------------------------------------
    # Early-exit cases
    # ------------------------------------------------------------------

    def test_skips_in_non_production(self):
        """Returns immediately and does nothing outside production."""
        service = self._service(_make_ssl_config())
        settings = _make_settings(environment="development")

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
        ):
            service.repair_if_inconsistent()

        mock_writer_cls.assert_not_called()

    def test_skips_when_no_ssl_config_row(self):
        """Returns immediately when there is no ssl_config row in the DB."""
        service = self._service(None)
        settings = _make_settings()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
        ):
            service.repair_if_inconsistent()

        mock_writer_cls.assert_not_called()

    def test_skips_when_mode_is_none(self):
        """Returns immediately when ssl_config.mode is None."""
        service = self._service(_make_ssl_config(mode=None))
        settings = _make_settings()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
        ):
            service.repair_if_inconsistent()

        mock_writer_cls.assert_not_called()

    def test_skips_when_domain_is_none(self):
        """Returns immediately when ssl_config.domain is None (incomplete config)."""
        service = self._service(_make_ssl_config(domain=None))
        settings = _make_settings()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
        ):
            service.repair_if_inconsistent()

        mock_writer_cls.assert_not_called()

    def test_skips_when_email_is_none(self):
        """Returns immediately when ssl_config.email is None (incomplete config)."""
        service = self._service(_make_ssl_config(email=None))
        settings = _make_settings()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
        ):
            service.repair_if_inconsistent()

        mock_writer_cls.assert_not_called()

    def test_skips_when_traefik_yml_is_consistent(self, tmp_path):
        """Returns immediately when traefik.yml already has certificatesResolvers."""
        traefik_yml = tmp_path / "traefik.yml"
        traefik_yml.write_text("certificatesResolvers:\n  letsencrypt:\n    acme: {}\n")

        service = self._service(_make_ssl_config())
        settings = _make_settings(traefik_config_dir=str(tmp_path))

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter"
            ) as mock_writer_cls,
        ):
            service.repair_if_inconsistent()

        mock_writer_cls.assert_not_called()

    # ------------------------------------------------------------------
    # Repair cases
    # ------------------------------------------------------------------

    def test_repairs_when_traefik_yml_missing(self):
        """Calls write_domain_config and restart_traefik when traefik.yml is absent."""
        service = self._service(_make_ssl_config())
        settings = _make_settings(traefik_config_dir="/nonexistent/dir", acme_ca_server=None)

        mock_writer = MagicMock()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter",
                return_value=mock_writer,
            ),
            patch.object(service, "restart_traefik") as mock_restart,
        ):
            service.repair_if_inconsistent()

        mock_writer.write_domain_config.assert_called_once_with(
            "example.com", "admin@example.com", ca_server=None
        )
        mock_restart.assert_called_once()

    def test_repairs_when_traefik_yml_has_no_certificates_resolvers(self, tmp_path):
        """Repairs when traefik.yml exists but contains only bootstrap content."""
        traefik_yml = tmp_path / "traefik.yml"
        traefik_yml.write_text(
            "entryPoints:\n  web:\n    address: ':80'\n"
            "providers:\n  file:\n    directory: /etc/traefik/dynamic\n"
        )

        service = self._service(_make_ssl_config())
        settings = _make_settings(traefik_config_dir=str(tmp_path), acme_ca_server=None)

        mock_writer = MagicMock()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter",
                return_value=mock_writer,
            ),
            patch.object(service, "restart_traefik") as mock_restart,
        ):
            service.repair_if_inconsistent()

        mock_writer.write_domain_config.assert_called_once_with(
            "example.com", "admin@example.com", ca_server=None
        )
        mock_restart.assert_called_once()

    def test_repair_passes_acme_ca_server_from_settings(self):
        """write_domain_config receives acme_ca_server from settings."""
        service = self._service(_make_ssl_config())
        settings = _make_settings(
            traefik_config_dir="/nonexistent/dir",
            acme_ca_server="https://pebble:14000/dir",
        )

        mock_writer = MagicMock()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter",
                return_value=mock_writer,
            ),
            patch.object(service, "restart_traefik"),
        ):
            service.repair_if_inconsistent()

        mock_writer.write_domain_config.assert_called_once_with(
            "example.com",
            "admin@example.com",
            ca_server="https://pebble:14000/dir",
        )

    # ------------------------------------------------------------------
    # Error handling
    # ------------------------------------------------------------------

    def test_does_not_restart_when_write_fails(self, caplog):
        """If write_domain_config raises, restart_traefik is NOT called."""
        service = self._service(_make_ssl_config())
        settings = _make_settings(traefik_config_dir="/nonexistent/dir")

        mock_writer = MagicMock()
        mock_writer.write_domain_config.side_effect = Exception("disk full")

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter",
                return_value=mock_writer,
            ),
            patch.object(service, "restart_traefik") as mock_restart,
            caplog.at_level(logging.ERROR),
        ):
            service.repair_if_inconsistent()  # must NOT raise

        mock_restart.assert_not_called()
        assert any("SSL config repair failed" in r.message for r in caplog.records)

    def test_does_not_raise_when_write_fails(self):
        """repair_if_inconsistent never raises even when write_domain_config fails."""
        service = self._service(_make_ssl_config())
        settings = _make_settings(traefik_config_dir="/nonexistent/dir")

        mock_writer = MagicMock()
        mock_writer.write_domain_config.side_effect = RuntimeError("unexpected")

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter",
                return_value=mock_writer,
            ),
            patch.object(service, "restart_traefik"),
        ):
            service.repair_if_inconsistent()  # must NOT raise

    def test_logs_warning_on_stale_config(self, caplog):
        """A WARNING is logged when a stale config is detected."""
        service = self._service(_make_ssl_config())
        settings = _make_settings(traefik_config_dir="/nonexistent/dir")

        mock_writer = MagicMock()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter",
                return_value=mock_writer,
            ),
            patch.object(service, "restart_traefik"),
            caplog.at_level(logging.WARNING),
        ):
            service.repair_if_inconsistent()

        assert any("Stale SSL config detected" in r.message for r in caplog.records)

    def test_logs_info_on_successful_repair(self, caplog):
        """An INFO message is logged after a successful repair."""
        service = self._service(_make_ssl_config())
        settings = _make_settings(traefik_config_dir="/nonexistent/dir")

        mock_writer = MagicMock()

        with (
            patch(
                "hyper_trader_api.services.ssl_setup_service.get_settings",
                return_value=settings,
            ),
            patch(
                "hyper_trader_api.services.ssl_setup_service.TraefikConfigWriter",
                return_value=mock_writer,
            ),
            patch.object(service, "restart_traefik"),
            caplog.at_level(logging.INFO),
        ):
            service.repair_if_inconsistent()

        assert any("SSL config repaired" in r.message for r in caplog.records)
