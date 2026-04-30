"""Traefik configuration file writer service."""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class TraefikConfigError(Exception):
    """Traefik configuration error."""

    pass


class TraefikConfigWriter:
    """Writes Traefik configuration files for SSL setup.

    Generates traefik.yml (static config) and dynamic/10-tls.yml (TLS routing)
    for Let's Encrypt (domain) mode. Uses directory provider pattern to coexist
    with bootstrap config (dynamic/00-bootstrap.yml).

    Args:
        config_dir: Directory where traefik.yml and dynamic/ subdirectory exist.
    """

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir

    def write_domain_config(
        self,
        domain: str,
        email: str,
        ca_server: str | None = None,
    ) -> None:
        """Write Traefik config files for Let's Encrypt (domain) mode.

        Creates traefik.yml (static config with ACME resolver) and
        dynamic/10-tls.yml (TLS routers that reference services defined
        in dynamic/00-bootstrap.yml).

        Args:
            domain: The domain name for routing and TLS certificate.
            email: Email address for Let's Encrypt ACME registration.
            ca_server: Optional ACME CA server URL. When None (default),
                Traefik uses Let's Encrypt's production endpoint. When set
                (e.g. Pebble's "https://pebble:14000/dir"), the resolver
                targets that directory instead — used for local SSL testing.

        Raises:
            TraefikConfigError: If writing configuration files fails.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            dynamic_dir = self.config_dir / "dynamic"
            dynamic_dir.mkdir(parents=True, exist_ok=True)

            traefik_config = self._build_domain_traefik_yml(email, ca_server)
            dynamic_config = self._build_domain_dynamic_yml(domain)

            self._write_yaml(self.config_dir / "traefik.yml", traefik_config)
            self._write_yaml(dynamic_dir / "10-tls.yml", dynamic_config)

            logger.info(f"Wrote domain Traefik config for {domain!r} to {self.config_dir}")

        except TraefikConfigError:
            raise
        except Exception as e:
            logger.error(f"Failed to write domain Traefik config: {e}")
            raise TraefikConfigError(f"Failed to write domain Traefik config: {e}") from e

    def backup_config(self) -> tuple[str, str | None] | None:
        """Back up current traefik.yml and dynamic/10-tls.yml files.

        Returns both file contents as strings. If traefik.yml doesn't exist,
        returns None (incomplete config). If only 10-tls.yml is missing,
        returns (traefik_content, None).

        Returns:
            A tuple of (traefik_yml_content, tls_yml_content | None), or None
            if traefik.yml is missing.
        """
        traefik_path = self.config_dir / "traefik.yml"
        tls_path = self.config_dir / "dynamic" / "10-tls.yml"

        if not traefik_path.exists():
            return None

        traefik_content = traefik_path.read_text()
        tls_content = tls_path.read_text() if tls_path.exists() else None

        return (traefik_content, tls_content)

    def restore_config(self, backup: tuple[str, str | None]) -> None:
        """Restore traefik.yml and dynamic/10-tls.yml from a backup.

        Args:
            backup: A tuple of (traefik_yml_content, tls_yml_content | None)
                as returned by backup_config(). If tls_yml_content is None,
                any existing dynamic/10-tls.yml is deleted (rollback case).

        Raises:
            TraefikConfigError: If restoring configuration files fails.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            dynamic_dir = self.config_dir / "dynamic"
            dynamic_dir.mkdir(parents=True, exist_ok=True)

            traefik_content, tls_content = backup
            (self.config_dir / "traefik.yml").write_text(traefik_content)

            tls_path = dynamic_dir / "10-tls.yml"
            if tls_content is not None:
                tls_path.write_text(tls_content)
            else:
                # Rollback case: delete TLS config if it exists
                if tls_path.exists():
                    tls_path.unlink()

            logger.info(f"Restored Traefik config to {self.config_dir}")

        except TraefikConfigError:
            raise
        except Exception as e:
            logger.error(f"Failed to restore Traefik config: {e}")
            raise TraefikConfigError(f"Failed to restore Traefik config: {e}") from e

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_domain_traefik_yml(
        self,
        email: str,
        ca_server: str | None = None,
    ) -> dict:  # type: ignore[type-arg]
        """Build traefik.yml config dict for domain (Let's Encrypt) mode."""
        acme: dict = {
            "email": email,
            "storage": "/letsencrypt/acme.json",
            "httpChallenge": {
                "entryPoint": "web",
            },
        }
        if ca_server is not None:
            acme["caServer"] = ca_server

        return {
            "entryPoints": {
                "web": {
                    "address": ":80",
                    "http": {
                        "redirections": {
                            "entryPoint": {
                                "to": "websecure",
                                "scheme": "https",
                            }
                        }
                    },
                },
                "websecure": {
                    "address": ":443",
                },
            },
            "ping": {},
            "certificatesResolvers": {
                "letsencrypt": {
                    "acme": acme,
                }
            },
            "providers": {
                "file": {
                    "directory": "/etc/traefik/dynamic",
                    "watch": True,
                }
            },
        }

    def _build_domain_dynamic_yml(self, domain: str) -> dict:  # type: ignore[type-arg]
        """Build dynamic/10-tls.yml config dict for domain (Let's Encrypt) mode.

        Defines only TLS routers that reference services already defined in
        dynamic/00-bootstrap.yml. Services are NOT redefined to avoid conflicts.
        Router names are suffixed with '-tls' to avoid name collisions with
        bootstrap routers (Traefik file provider de-duplicates by name).
        """
        return {
            "http": {
                "routers": {
                    "health-tls": {
                        "rule": f"Host(`{domain}`) && Path(`/health`)",
                        "service": "api",
                        "entryPoints": ["websecure"],
                        "priority": 20,
                        "tls": {
                            "certResolver": "letsencrypt",
                        },
                    },
                    "api-tls": {
                        "rule": f"Host(`{domain}`) && PathPrefix(`/api`)",
                        "service": "api",
                        "entryPoints": ["websecure"],
                        "priority": 10,
                        "tls": {
                            "certResolver": "letsencrypt",
                        },
                    },
                    "web-tls": {
                        "rule": f"Host(`{domain}`)",
                        "service": "web",
                        "entryPoints": ["websecure"],
                        "priority": 1,
                        "tls": {
                            "certResolver": "letsencrypt",
                        },
                    },
                },
            }
        }

    def _write_yaml(self, path: Path, data: dict) -> None:  # type: ignore[type-arg]
        """Serialize data to YAML and write to path."""
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
