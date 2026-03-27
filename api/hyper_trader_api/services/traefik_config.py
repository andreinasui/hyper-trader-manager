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

    Generates traefik.yml and dynamic.yml for either Let's Encrypt (domain)
    mode or self-signed certificate (IP-only) mode.

    Args:
        config_dir: Directory where traefik.yml and dynamic.yml will be written.
    """

    def __init__(self, config_dir: Path) -> None:
        self.config_dir = config_dir

    def write_domain_config(self, domain: str, email: str) -> None:
        """Write Traefik config files for Let's Encrypt (domain) mode.

        Creates traefik.yml with ACME resolver and dynamic.yml with
        Host-based routing rules using the provided domain.

        Args:
            domain: The domain name for routing and TLS certificate.
            email: Email address for Let's Encrypt ACME registration.

        Raises:
            TraefikConfigError: If writing configuration files fails.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            traefik_config = self._build_domain_traefik_yml(email)
            dynamic_config = self._build_domain_dynamic_yml(domain)

            self._write_yaml(self.config_dir / "traefik.yml", traefik_config)
            self._write_yaml(self.config_dir / "dynamic.yml", dynamic_config)

            logger.info(f"Wrote domain Traefik config for {domain!r} to {self.config_dir}")

        except TraefikConfigError:
            raise
        except Exception as e:
            logger.error(f"Failed to write domain Traefik config: {e}")
            raise TraefikConfigError(f"Failed to write domain Traefik config: {e}") from e

    def write_ip_only_config(self) -> None:
        """Write Traefik config files for self-signed certificate (IP-only) mode.

        Creates traefik.yml without ACME and dynamic.yml with PathPrefix-based
        routing rules and TLS pointing to /certs/cert.pem and /certs/key.pem.

        Raises:
            TraefikConfigError: If writing configuration files fails.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            traefik_config = self._build_ip_only_traefik_yml()
            dynamic_config = self._build_ip_only_dynamic_yml()

            self._write_yaml(self.config_dir / "traefik.yml", traefik_config)
            self._write_yaml(self.config_dir / "dynamic.yml", dynamic_config)

            logger.info(f"Wrote IP-only Traefik config to {self.config_dir}")

        except TraefikConfigError:
            raise
        except Exception as e:
            logger.error(f"Failed to write IP-only Traefik config: {e}")
            raise TraefikConfigError(f"Failed to write IP-only Traefik config: {e}") from e

    def backup_config(self) -> tuple[str, str] | None:
        """Back up current traefik.yml and dynamic.yml files.

        Returns both file contents as strings, or None if either file does
        not exist (incomplete configuration).

        Returns:
            A tuple of (traefik_yml_content, dynamic_yml_content), or None
            if the configuration is incomplete or missing.
        """
        traefik_path = self.config_dir / "traefik.yml"
        dynamic_path = self.config_dir / "dynamic.yml"

        if not traefik_path.exists() or not dynamic_path.exists():
            return None

        return (traefik_path.read_text(), dynamic_path.read_text())

    def restore_config(self, backup: tuple[str, str]) -> None:
        """Restore traefik.yml and dynamic.yml from a backup.

        Args:
            backup: A tuple of (traefik_yml_content, dynamic_yml_content)
                as returned by backup_config().

        Raises:
            TraefikConfigError: If restoring configuration files fails.
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            traefik_content, dynamic_content = backup
            (self.config_dir / "traefik.yml").write_text(traefik_content)
            (self.config_dir / "dynamic.yml").write_text(dynamic_content)

            logger.info(f"Restored Traefik config to {self.config_dir}")

        except TraefikConfigError:
            raise
        except Exception as e:
            logger.error(f"Failed to restore Traefik config: {e}")
            raise TraefikConfigError(f"Failed to restore Traefik config: {e}") from e

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _dynamic_yml_path(self) -> str:
        """Return the absolute path string for dynamic.yml."""
        return str((self.config_dir / "dynamic.yml").absolute())

    def _build_domain_traefik_yml(self, email: str) -> dict:  # type: ignore[type-arg]
        """Build traefik.yml config dict for domain (Let's Encrypt) mode."""
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
            "certificatesResolvers": {
                "letsencrypt": {
                    "acme": {
                        "email": email,
                        "storage": "/letsencrypt/acme.json",
                        "httpChallenge": {
                            "entryPoint": "web",
                        },
                    }
                }
            },
            "providers": {
                "file": {
                    "filename": self._dynamic_yml_path(),
                    "watch": True,
                }
            },
        }

    def _build_domain_dynamic_yml(self, domain: str) -> dict:  # type: ignore[type-arg]
        """Build dynamic.yml config dict for domain (Let's Encrypt) mode."""
        return {
            "http": {
                "routers": {
                    "health": {
                        "rule": f'Host(`{domain}`) && Path(`/health`)',
                        "service": "api",
                        "entryPoints": ["websecure"],
                        "priority": 20,
                        "tls": {
                            "certResolver": "letsencrypt",
                        },
                    },
                    "api": {
                        "rule": f'Host(`{domain}`) && PathPrefix(`/api`)',
                        "service": "api",
                        "entryPoints": ["websecure"],
                        "priority": 10,
                        "tls": {
                            "certResolver": "letsencrypt",
                        },
                    },
                    "web": {
                        "rule": f'Host(`{domain}`)',
                        "service": "web",
                        "entryPoints": ["websecure"],
                        "priority": 1,
                        "tls": {
                            "certResolver": "letsencrypt",
                        },
                    },
                },
                "services": self._build_services(),
            }
        }

    def _build_ip_only_traefik_yml(self) -> dict:  # type: ignore[type-arg]
        """Build traefik.yml config dict for IP-only (self-signed) mode."""
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
            "providers": {
                "file": {
                    "filename": self._dynamic_yml_path(),
                    "watch": True,
                }
            },
        }

    def _build_ip_only_dynamic_yml(self) -> dict:  # type: ignore[type-arg]
        """Build dynamic.yml config dict for IP-only (self-signed) mode."""
        return {
            "tls": {
                "certificates": [
                    {
                        "certFile": "/certs/cert.pem",
                        "keyFile": "/certs/key.pem",
                    }
                ]
            },
            "http": {
                "routers": {
                    "health": {
                        "rule": "Path(`/health`)",
                        "service": "api",
                        "entryPoints": ["websecure"],
                        "priority": 20,
                        "tls": {},
                    },
                    "api": {
                        "rule": "PathPrefix(`/api`)",
                        "service": "api",
                        "entryPoints": ["websecure"],
                        "priority": 10,
                        "tls": {},
                    },
                    "web": {
                        "rule": "PathPrefix(`/`)",
                        "service": "web",
                        "entryPoints": ["websecure"],
                        "priority": 1,
                        "tls": {},
                    },
                },
                "services": self._build_services(),
            },
        }

    def _build_services(self) -> dict:  # type: ignore[type-arg]
        """Build shared services config (api and web)."""
        return {
            "api": {
                "loadBalancer": {
                    "servers": [{"url": "http://api:8000"}],
                    "healthCheck": {
                        "path": "/health",
                        "interval": "10s",
                        "timeout": "5s",
                    },
                }
            },
            "web": {
                "loadBalancer": {
                    "servers": [{"url": "http://web:80"}],
                    "healthCheck": {
                        "path": "/health",
                        "interval": "10s",
                        "timeout": "5s",
                    },
                }
            },
        }

    def _write_yaml(self, path: Path, data: dict) -> None:  # type: ignore[type-arg]
        """Serialize data to YAML and write to path."""
        path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
