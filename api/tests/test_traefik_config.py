"""
Tests for TraefikConfigWriter service.

Covers:
- TraefikConfigWriter.write_domain_config: writes Let's Encrypt mode configs
- TraefikConfigWriter.backup_config: backs up existing configs
- TraefikConfigWriter.restore_config: restores from backup
"""

from pathlib import Path

import yaml

from hyper_trader_api.services.traefik_config import (
    TraefikConfigError,
    TraefikConfigWriter,
)


class TestTraefikConfigError:
    """Tests for TraefikConfigError exception."""

    def test_is_exception(self):
        """TraefikConfigError is a subclass of Exception."""
        err = TraefikConfigError("something went wrong")
        assert isinstance(err, Exception)
        assert str(err) == "something went wrong"


class TestTraefikConfigWriterInit:
    """Tests for TraefikConfigWriter initialization."""

    def test_init_stores_config_dir(self, tmp_path: Path):
        """TraefikConfigWriter stores the config directory."""
        writer = TraefikConfigWriter(tmp_path)
        assert writer.config_dir == tmp_path


class TestWriteDomainConfig:
    """Tests for write_domain_config (Let's Encrypt mode)."""

    def test_creates_traefik_yml(self, tmp_path: Path):
        """write_domain_config creates traefik.yml in config_dir."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        assert (tmp_path / "traefik.yml").exists()

    def test_creates_dynamic_tls_yml(self, tmp_path: Path):
        """write_domain_config creates dynamic/10-tls.yml in config_dir."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        assert (tmp_path / "dynamic" / "10-tls.yml").exists()

    def test_traefik_yml_is_valid_yaml(self, tmp_path: Path):
        """traefik.yml produced by write_domain_config is valid YAML."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        content = (tmp_path / "traefik.yml").read_text()
        config = yaml.safe_load(content)
        assert isinstance(config, dict)

    def test_dynamic_tls_yml_is_valid_yaml(self, tmp_path: Path):
        """dynamic/10-tls.yml produced by write_domain_config is valid YAML."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        content = (tmp_path / "dynamic" / "10-tls.yml").read_text()
        config = yaml.safe_load(content)
        assert isinstance(config, dict)

    def test_traefik_yml_has_web_entrypoint_on_port_80(self, tmp_path: Path):
        """traefik.yml has entryPoint 'web' on :80."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        assert config["entryPoints"]["web"]["address"] == ":80"

    def test_traefik_yml_has_websecure_entrypoint_on_port_443(self, tmp_path: Path):
        """traefik.yml has entryPoint 'websecure' on :443."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        assert config["entryPoints"]["websecure"]["address"] == ":443"

    def test_traefik_yml_has_http_to_https_redirect(self, tmp_path: Path):
        """traefik.yml redirects HTTP to HTTPS on the web entrypoint."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        redirects = config["entryPoints"]["web"]["http"]["redirections"]
        assert redirects["entryPoint"]["to"] == "websecure"
        assert redirects["entryPoint"]["scheme"] == "https"

    def test_traefik_yml_has_letsencrypt_resolver(self, tmp_path: Path):
        """traefik.yml has a certificatesResolvers entry named 'letsencrypt'."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        assert "letsencrypt" in config["certificatesResolvers"]

    def test_traefik_yml_letsencrypt_uses_provided_email(self, tmp_path: Path):
        """traefik.yml ACME config uses the provided email address."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        acme = config["certificatesResolvers"]["letsencrypt"]["acme"]
        assert acme["email"] == "admin@example.com"

    def test_traefik_yml_providers_file_points_to_dynamic_directory(self, tmp_path: Path):
        """traefik.yml providers.file.directory points to /etc/traefik/dynamic."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        directory = config["providers"]["file"]["directory"]
        assert directory == "/etc/traefik/dynamic"

    def test_traefik_yml_enables_ping_for_healthcheck(self, tmp_path: Path):
        """traefik.yml enables ping endpoint so the container healthcheck can succeed."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        assert "ping" in config, "ping must be enabled for `traefik healthcheck` CLI"

    def test_dynamic_tls_yml_has_health_router_with_host_rule(self, tmp_path: Path):
        """dynamic/10-tls.yml health router uses Host rule matching the domain."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic" / "10-tls.yml").read_text())
        health_rule = config["http"]["routers"]["health-tls"]["rule"]
        assert "example.com" in health_rule
        assert "Host" in health_rule

    def test_dynamic_tls_yml_has_api_router_with_host_rule(self, tmp_path: Path):
        """dynamic/10-tls.yml api router uses Host rule matching the domain."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic" / "10-tls.yml").read_text())
        api_rule = config["http"]["routers"]["api-tls"]["rule"]
        assert "example.com" in api_rule
        assert "Host" in api_rule

    def test_dynamic_tls_yml_has_web_router_with_host_rule(self, tmp_path: Path):
        """dynamic/10-tls.yml web router uses Host rule matching the domain."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic" / "10-tls.yml").read_text())
        web_rule = config["http"]["routers"]["web-tls"]["rule"]
        assert "example.com" in web_rule
        assert "Host" in web_rule

    def test_dynamic_tls_yml_routers_use_letsencrypt_cert_resolver(self, tmp_path: Path):
        """dynamic/10-tls.yml routers have tls.certResolver set to 'letsencrypt'."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic" / "10-tls.yml").read_text())
        for router_name in ("health-tls", "api-tls", "web-tls"):
            router = config["http"]["routers"][router_name]
            assert router["tls"]["certResolver"] == "letsencrypt", (
                f"Router '{router_name}' should have certResolver=letsencrypt"
            )

    def test_dynamic_tls_yml_does_not_define_services(self, tmp_path: Path):
        """dynamic/10-tls.yml does NOT define services (relies on bootstrap config)."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic" / "10-tls.yml").read_text())
        # The TLS config should only have routers, NOT services
        assert "services" not in config.get("http", {})

    def test_write_domain_config_creates_parent_dirs_if_missing(self, tmp_path: Path):
        """write_domain_config creates config_dir if it does not exist."""
        config_dir = tmp_path / "nested" / "traefik"
        writer = TraefikConfigWriter(config_dir)
        writer.write_domain_config("example.com", "admin@example.com")
        assert (config_dir / "traefik.yml").exists()
        assert (config_dir / "dynamic" / "10-tls.yml").exists()

    def test_write_domain_config_does_not_touch_bootstrap_file(self, tmp_path: Path):
        """write_domain_config does NOT modify existing dynamic/00-bootstrap.yml."""
        writer = TraefikConfigWriter(tmp_path)

        # Create a bootstrap file first
        bootstrap_dir = tmp_path / "dynamic"
        bootstrap_dir.mkdir(parents=True, exist_ok=True)
        bootstrap_content = "# Bootstrap config\nhttp:\n  services:\n    api:\n      loadBalancer:\n        servers:\n          - url: http://api:8000\n"
        bootstrap_path = bootstrap_dir / "00-bootstrap.yml"
        bootstrap_path.write_text(bootstrap_content)

        # Write domain config
        writer.write_domain_config("example.com", "admin@example.com")

        # Bootstrap should remain unchanged
        assert bootstrap_path.exists()
        assert bootstrap_path.read_text() == bootstrap_content


class TestBackupConfig:
    """Tests for backup_config method."""

    def test_returns_none_when_no_files_exist(self, tmp_path: Path):
        """backup_config returns None when traefik.yml does not exist."""
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is None

    def test_returns_tuple_when_traefik_yml_exists(self, tmp_path: Path):
        """backup_config returns a tuple when traefik.yml exists."""
        (tmp_path / "traefik.yml").write_text("traefik: config")
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_backup_contains_traefik_yml_content(self, tmp_path: Path):
        """backup_config first element is the content of traefik.yml."""
        traefik_content = "traefik: config\nversion: 1"
        (tmp_path / "traefik.yml").write_text(traefik_content)
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is not None
        assert result[0] == traefik_content

    def test_backup_contains_tls_yml_content_when_exists(self, tmp_path: Path):
        """backup_config second element is the content of dynamic/10-tls.yml if it exists."""
        tls_content = "http:\n  routers:\n    web: {}"
        (tmp_path / "traefik.yml").write_text("traefik: config")
        dynamic_dir = tmp_path / "dynamic"
        dynamic_dir.mkdir()
        (dynamic_dir / "10-tls.yml").write_text(tls_content)
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is not None
        assert result[1] == tls_content

    def test_backup_tls_is_none_when_only_traefik_yml_exists(self, tmp_path: Path):
        """backup_config returns (traefik_content, None) when only traefik.yml exists."""
        (tmp_path / "traefik.yml").write_text("traefik: config")
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is not None
        assert result[0] == "traefik: config"
        assert result[1] is None


class TestRestoreConfig:
    """Tests for restore_config method."""

    def test_restores_traefik_yml_from_backup(self, tmp_path: Path):
        """restore_config writes traefik.yml content from backup tuple."""
        traefik_content = "traefik: original\n"
        tls_content = "http:\n  routers: {}\n"
        writer = TraefikConfigWriter(tmp_path)
        writer.restore_config((traefik_content, tls_content))
        assert (tmp_path / "traefik.yml").read_text() == traefik_content

    def test_restores_tls_yml_from_backup(self, tmp_path: Path):
        """restore_config writes dynamic/10-tls.yml content from backup tuple."""
        traefik_content = "traefik: original\n"
        tls_content = "http:\n  routers: {}\n"
        writer = TraefikConfigWriter(tmp_path)
        writer.restore_config((traefik_content, tls_content))
        assert (tmp_path / "dynamic" / "10-tls.yml").read_text() == tls_content

    def test_restore_overwrites_existing_files(self, tmp_path: Path):
        """restore_config overwrites existing config files with backup content."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")

        backup = ("traefik: restored\n", "http:\n  routers:\n    restored: {}\n")
        writer.restore_config(backup)

        assert (tmp_path / "traefik.yml").read_text() == "traefik: restored\n"
        assert (
            tmp_path / "dynamic" / "10-tls.yml"
        ).read_text() == "http:\n  routers:\n    restored: {}\n"

    def test_restore_creates_parent_dirs_if_missing(self, tmp_path: Path):
        """restore_config creates config_dir if it does not exist."""
        config_dir = tmp_path / "new" / "traefik"
        writer = TraefikConfigWriter(config_dir)
        writer.restore_config(("traefik: content\n", "http:\n  routers: {}\n"))
        assert (config_dir / "traefik.yml").exists()
        assert (config_dir / "dynamic" / "10-tls.yml").exists()

    def test_restore_deletes_tls_yml_when_backup_is_none(self, tmp_path: Path):
        """restore_config deletes dynamic/10-tls.yml when backup tls_content is None (rollback case)."""
        writer = TraefikConfigWriter(tmp_path)

        # First write a full config
        writer.write_domain_config("example.com", "admin@example.com")
        assert (tmp_path / "dynamic" / "10-tls.yml").exists()

        # Now restore with None for tls_content (rollback)
        writer.restore_config(("traefik: bootstrap\n", None))

        # TLS file should be deleted
        assert not (tmp_path / "dynamic" / "10-tls.yml").exists()
        assert (tmp_path / "traefik.yml").exists()


class TestTraefikConfigWriterRoundTrip:
    """Integration tests: backup → write → restore round-trip."""

    def test_backup_and_restore_preserves_config(self, tmp_path: Path):
        """Writing a new config and restoring a backup returns to original state."""
        writer = TraefikConfigWriter(tmp_path)

        # Write initial domain config
        writer.write_domain_config("initial.com", "initial@example.com")
        original_traefik = (tmp_path / "traefik.yml").read_text()
        original_tls = (tmp_path / "dynamic" / "10-tls.yml").read_text()

        # Backup
        backup = writer.backup_config()
        assert backup is not None

        # Overwrite with different domain config
        writer.write_domain_config("overwrite.com", "overwrite@example.com")
        assert (tmp_path / "traefik.yml").read_text() != original_traefik

        # Restore
        writer.restore_config(backup)
        assert (tmp_path / "traefik.yml").read_text() == original_traefik
        assert (tmp_path / "dynamic" / "10-tls.yml").read_text() == original_tls
