"""
Tests for Traefik config writer service.

Covers:
- TraefikConfigError: raised on failure
- TraefikConfigWriter.write_domain_config: writes Let's Encrypt mode configs
- TraefikConfigWriter.write_ip_only_config: writes self-signed cert mode configs
- TraefikConfigWriter.backup_config: backs up current config files
- TraefikConfigWriter.restore_config: restores config from backup
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

    def test_creates_dynamic_yml(self, tmp_path: Path):
        """write_domain_config creates dynamic.yml in config_dir."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        assert (tmp_path / "dynamic.yml").exists()

    def test_traefik_yml_is_valid_yaml(self, tmp_path: Path):
        """traefik.yml produced by write_domain_config is valid YAML."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        content = (tmp_path / "traefik.yml").read_text()
        config = yaml.safe_load(content)
        assert isinstance(config, dict)

    def test_dynamic_yml_is_valid_yaml(self, tmp_path: Path):
        """dynamic.yml produced by write_domain_config is valid YAML."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        content = (tmp_path / "dynamic.yml").read_text()
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

    def test_traefik_yml_providers_file_points_to_dynamic_yml(self, tmp_path: Path):
        """traefik.yml providers.file.filename points to dynamic.yml."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        filename = config["providers"]["file"]["filename"]
        assert "dynamic.yml" in filename

    def test_dynamic_yml_has_health_router_with_host_rule(self, tmp_path: Path):
        """dynamic.yml health router uses Host rule matching the domain."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        health_rule = config["http"]["routers"]["health"]["rule"]
        assert "example.com" in health_rule
        assert "Host" in health_rule

    def test_dynamic_yml_has_api_router_with_host_rule(self, tmp_path: Path):
        """dynamic.yml api router uses Host rule matching the domain."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        api_rule = config["http"]["routers"]["api"]["rule"]
        assert "example.com" in api_rule
        assert "Host" in api_rule

    def test_dynamic_yml_has_web_router_with_host_rule(self, tmp_path: Path):
        """dynamic.yml web router uses Host rule matching the domain."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        web_rule = config["http"]["routers"]["web"]["rule"]
        assert "example.com" in web_rule
        assert "Host" in web_rule

    def test_dynamic_yml_routers_use_letsencrypt_cert_resolver(self, tmp_path: Path):
        """dynamic.yml routers have tls.certResolver set to 'letsencrypt'."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        for router_name in ("health", "api", "web"):
            router = config["http"]["routers"][router_name]
            assert router["tls"]["certResolver"] == "letsencrypt", (
                f"Router '{router_name}' should have certResolver=letsencrypt"
            )

    def test_dynamic_yml_api_service_points_to_api_container(self, tmp_path: Path):
        """dynamic.yml api service backend URL is http://api:8000."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        servers = config["http"]["services"]["api"]["loadBalancer"]["servers"]
        urls = [s["url"] for s in servers]
        assert "http://api:8000" in urls

    def test_dynamic_yml_web_service_points_to_web_container(self, tmp_path: Path):
        """dynamic.yml web service backend URL is http://web:80."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_domain_config("example.com", "admin@example.com")
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        servers = config["http"]["services"]["web"]["loadBalancer"]["servers"]
        urls = [s["url"] for s in servers]
        assert "http://web:80" in urls

    def test_write_domain_config_creates_parent_dirs_if_missing(self, tmp_path: Path):
        """write_domain_config creates config_dir if it does not exist."""
        config_dir = tmp_path / "nested" / "traefik"
        writer = TraefikConfigWriter(config_dir)
        writer.write_domain_config("example.com", "admin@example.com")
        assert (config_dir / "traefik.yml").exists()
        assert (config_dir / "dynamic.yml").exists()


class TestWriteIpOnlyConfig:
    """Tests for write_ip_only_config (self-signed cert mode)."""

    def test_creates_traefik_yml(self, tmp_path: Path):
        """write_ip_only_config creates traefik.yml in config_dir."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        assert (tmp_path / "traefik.yml").exists()

    def test_creates_dynamic_yml(self, tmp_path: Path):
        """write_ip_only_config creates dynamic.yml in config_dir."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        assert (tmp_path / "dynamic.yml").exists()

    def test_traefik_yml_is_valid_yaml(self, tmp_path: Path):
        """traefik.yml produced by write_ip_only_config is valid YAML."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        assert isinstance(config, dict)

    def test_dynamic_yml_is_valid_yaml(self, tmp_path: Path):
        """dynamic.yml produced by write_ip_only_config is valid YAML."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        assert isinstance(config, dict)

    def test_traefik_yml_has_web_entrypoint_on_port_80(self, tmp_path: Path):
        """IP-only traefik.yml has entryPoint 'web' on :80."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        assert config["entryPoints"]["web"]["address"] == ":80"

    def test_traefik_yml_has_websecure_entrypoint_on_port_443(self, tmp_path: Path):
        """IP-only traefik.yml has entryPoint 'websecure' on :443."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        assert config["entryPoints"]["websecure"]["address"] == ":443"

    def test_traefik_yml_has_http_to_https_redirect(self, tmp_path: Path):
        """IP-only traefik.yml redirects HTTP to HTTPS."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        redirects = config["entryPoints"]["web"]["http"]["redirections"]
        assert redirects["entryPoint"]["to"] == "websecure"
        assert redirects["entryPoint"]["scheme"] == "https"

    def test_traefik_yml_has_no_certificates_resolvers(self, tmp_path: Path):
        """IP-only traefik.yml does NOT include certificatesResolvers (no ACME)."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        assert "certificatesResolvers" not in config

    def test_traefik_yml_has_providers_file(self, tmp_path: Path):
        """IP-only traefik.yml has providers.file pointing to dynamic.yml."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "traefik.yml").read_text())
        filename = config["providers"]["file"]["filename"]
        assert "dynamic.yml" in filename

    def test_dynamic_yml_has_tls_certificates_with_cert_pem(self, tmp_path: Path):
        """IP-only dynamic.yml tls.certificates certFile is /certs/cert.pem."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        certs = config["tls"]["certificates"]
        assert any(c["certFile"] == "/certs/cert.pem" for c in certs)

    def test_dynamic_yml_has_tls_certificates_with_key_pem(self, tmp_path: Path):
        """IP-only dynamic.yml tls.certificates keyFile is /certs/key.pem."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        certs = config["tls"]["certificates"]
        assert any(c["keyFile"] == "/certs/key.pem" for c in certs)

    def test_dynamic_yml_health_router_uses_path_prefix_rule(self, tmp_path: Path):
        """IP-only dynamic.yml health router uses PathPrefix rule (no Host)."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        health_rule = config["http"]["routers"]["health"]["rule"]
        assert "Host" not in health_rule
        assert "Path" in health_rule

    def test_dynamic_yml_api_router_uses_path_prefix_rule(self, tmp_path: Path):
        """IP-only dynamic.yml api router uses PathPrefix rule (no Host)."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        api_rule = config["http"]["routers"]["api"]["rule"]
        assert "Host" not in api_rule
        assert "PathPrefix" in api_rule

    def test_dynamic_yml_web_router_uses_path_prefix_rule(self, tmp_path: Path):
        """IP-only dynamic.yml web router uses PathPrefix rule (no Host)."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        web_rule = config["http"]["routers"]["web"]["rule"]
        assert "Host" not in web_rule
        assert "PathPrefix" in web_rule

    def test_dynamic_yml_routers_have_tls_enabled(self, tmp_path: Path):
        """IP-only dynamic.yml routers have tls section enabled."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        for router_name in ("health", "api", "web"):
            router = config["http"]["routers"][router_name]
            assert "tls" in router, f"Router '{router_name}' should have tls section"

    def test_dynamic_yml_api_service_points_to_api_container(self, tmp_path: Path):
        """IP-only dynamic.yml api service backend URL is http://api:8000."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        servers = config["http"]["services"]["api"]["loadBalancer"]["servers"]
        urls = [s["url"] for s in servers]
        assert "http://api:8000" in urls

    def test_dynamic_yml_web_service_points_to_web_container(self, tmp_path: Path):
        """IP-only dynamic.yml web service backend URL is http://web:80."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()
        config = yaml.safe_load((tmp_path / "dynamic.yml").read_text())
        servers = config["http"]["services"]["web"]["loadBalancer"]["servers"]
        urls = [s["url"] for s in servers]
        assert "http://web:80" in urls


class TestBackupConfig:
    """Tests for backup_config method."""

    def test_returns_none_when_no_files_exist(self, tmp_path: Path):
        """backup_config returns None when neither config file exists."""
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is None

    def test_returns_tuple_of_two_strings_when_files_exist(self, tmp_path: Path):
        """backup_config returns a tuple of (traefik_yml_content, dynamic_yml_content)."""
        (tmp_path / "traefik.yml").write_text("traefik: config")
        (tmp_path / "dynamic.yml").write_text("dynamic: config")
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_backup_contains_traefik_yml_content(self, tmp_path: Path):
        """backup_config first element is the content of traefik.yml."""
        traefik_content = "traefik: config\nversion: 1"
        (tmp_path / "traefik.yml").write_text(traefik_content)
        (tmp_path / "dynamic.yml").write_text("dynamic: config")
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is not None
        assert result[0] == traefik_content

    def test_backup_contains_dynamic_yml_content(self, tmp_path: Path):
        """backup_config second element is the content of dynamic.yml."""
        dynamic_content = "dynamic: config\nrouters: {}"
        (tmp_path / "traefik.yml").write_text("traefik: config")
        (tmp_path / "dynamic.yml").write_text(dynamic_content)
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is not None
        assert result[1] == dynamic_content

    def test_returns_none_when_only_traefik_yml_exists(self, tmp_path: Path):
        """backup_config returns None when only traefik.yml exists (incomplete config)."""
        (tmp_path / "traefik.yml").write_text("traefik: config")
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is None

    def test_returns_none_when_only_dynamic_yml_exists(self, tmp_path: Path):
        """backup_config returns None when only dynamic.yml exists (incomplete config)."""
        (tmp_path / "dynamic.yml").write_text("dynamic: config")
        writer = TraefikConfigWriter(tmp_path)
        result = writer.backup_config()
        assert result is None


class TestRestoreConfig:
    """Tests for restore_config method."""

    def test_restores_traefik_yml_from_backup(self, tmp_path: Path):
        """restore_config writes traefik.yml content from backup tuple."""
        traefik_content = "traefik: original\n"
        dynamic_content = "dynamic: original\n"
        writer = TraefikConfigWriter(tmp_path)
        writer.restore_config((traefik_content, dynamic_content))
        assert (tmp_path / "traefik.yml").read_text() == traefik_content

    def test_restores_dynamic_yml_from_backup(self, tmp_path: Path):
        """restore_config writes dynamic.yml content from backup tuple."""
        traefik_content = "traefik: original\n"
        dynamic_content = "dynamic: original\n"
        writer = TraefikConfigWriter(tmp_path)
        writer.restore_config((traefik_content, dynamic_content))
        assert (tmp_path / "dynamic.yml").read_text() == dynamic_content

    def test_restore_overwrites_existing_files(self, tmp_path: Path):
        """restore_config overwrites existing config files with backup content."""
        writer = TraefikConfigWriter(tmp_path)
        writer.write_ip_only_config()

        backup = ("traefik: restored\n", "dynamic: restored\n")
        writer.restore_config(backup)

        assert (tmp_path / "traefik.yml").read_text() == "traefik: restored\n"
        assert (tmp_path / "dynamic.yml").read_text() == "dynamic: restored\n"

    def test_restore_creates_parent_dirs_if_missing(self, tmp_path: Path):
        """restore_config creates config_dir if it does not exist."""
        config_dir = tmp_path / "new" / "traefik"
        writer = TraefikConfigWriter(config_dir)
        writer.restore_config(("traefik: content\n", "dynamic: content\n"))
        assert (config_dir / "traefik.yml").exists()
        assert (config_dir / "dynamic.yml").exists()


class TestTraefikConfigWriterRoundTrip:
    """Integration tests: backup → write → restore round-trip."""

    def test_backup_and_restore_preserves_config(self, tmp_path: Path):
        """Writing a new config and restoring a backup returns to original state."""
        writer = TraefikConfigWriter(tmp_path)

        # Write initial domain config
        writer.write_domain_config("initial.com", "initial@example.com")
        original_traefik = (tmp_path / "traefik.yml").read_text()
        original_dynamic = (tmp_path / "dynamic.yml").read_text()

        # Backup
        backup = writer.backup_config()
        assert backup is not None

        # Overwrite with IP-only config
        writer.write_ip_only_config()
        assert (tmp_path / "traefik.yml").read_text() != original_traefik

        # Restore
        writer.restore_config(backup)
        assert (tmp_path / "traefik.yml").read_text() == original_traefik
        assert (tmp_path / "dynamic.yml").read_text() == original_dynamic
