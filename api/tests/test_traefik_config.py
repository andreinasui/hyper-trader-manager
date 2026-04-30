"""Tests for TraefikConfigWriter."""

from pathlib import Path

import yaml

from hyper_trader_api.services.traefik_config import TraefikConfigWriter


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


class TestWriteDomainConfigCAServer:
    """Verify that the optional ca_server kwarg flows into traefik.yml."""

    def test_ca_server_omitted_when_none(self, tmp_path: Path) -> None:
        """Default behaviour: no caServer field in the ACME resolver."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")

        cfg = _read_yaml(tmp_path / "traefik.yml")
        acme = cfg["certificatesResolvers"]["letsencrypt"]["acme"]

        assert "caServer" not in acme
        assert acme["email"] == "admin@example.com"

    def test_ca_server_emitted_when_provided(self, tmp_path: Path) -> None:
        """Explicit ca_server is rendered into the ACME resolver block."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config(
            "hypertrader.localtest.me",
            "admin@example.com",
            ca_server="https://pebble:14000/dir",
        )

        cfg = _read_yaml(tmp_path / "traefik.yml")
        acme = cfg["certificatesResolvers"]["letsencrypt"]["acme"]

        assert acme["caServer"] == "https://pebble:14000/dir"
        assert acme["email"] == "admin@example.com"

    def test_ca_server_does_not_affect_dynamic_routers(self, tmp_path: Path) -> None:
        """The dynamic file is unaffected by ca_server."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config(
            "hypertrader.localtest.me",
            "admin@example.com",
            ca_server="https://pebble:14000/dir",
        )

        dyn = _read_yaml(tmp_path / "dynamic" / "10-tls.yml")
        rule = dyn["http"]["routers"]["web-tls"]["rule"]
        assert rule == "Host(`hypertrader.localtest.me`)"
