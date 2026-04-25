"""SSL setup orchestration service."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import docker
import docker.errors
from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.models.ssl_config import SSLConfig
from hyper_trader_api.services.cert_generator import generate_self_signed_cert
from hyper_trader_api.services.traefik_config import TraefikConfigWriter

logger = logging.getLogger(__name__)


class SSLSetupError(Exception):
    """SSL setup orchestration error."""

    pass


class SSLSetupService:
    """Orchestrates SSL setup for HyperTrader.

    Coordinates Traefik configuration, certificate generation, and Docker
    container management to set up HTTPS for the application.

    Args:
        db: SQLAlchemy database session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_ssl_config(self) -> SSLConfig | None:
        """Get the current SSL configuration from the database.

        Returns:
            The SSLConfig singleton (id=1), or None if not yet configured.
        """
        return self.db.get(SSLConfig, 1)

    def is_ssl_configured(self) -> bool:
        """Check if SSL has already been configured.

        Returns:
            True if SSL mode has been set, False otherwise.
        """
        config = self.get_ssl_config()
        if config is None:
            return False
        return config.mode is not None

    def configure_domain_ssl(self, domain: str, email: str) -> str:
        """Configure Let's Encrypt SSL for a domain.

        Writes Traefik config, creates acme.json, and restarts Traefik.
        On failure, restores the previous Traefik config.

        Args:
            domain: The domain name for Let's Encrypt certificate.
            email: Email address for Let's Encrypt ACME registration.

        Returns:
            HTTPS redirect URL (https://<domain>).

        Raises:
            SSLSetupError: If configuration fails (backup is restored).
        """
        settings = get_settings()
        data_dir = Path(settings.data_dir)
        traefik_config_dir = data_dir / "traefik"
        letsencrypt_dir = data_dir / "letsencrypt"
        acme_json_path = letsencrypt_dir / "acme.json"

        writer = TraefikConfigWriter(traefik_config_dir)
        backup = writer.backup_config()

        try:
            # Write new Traefik config for domain mode
            writer.write_domain_config(domain, email)

            # Create acme.json with correct permissions (0o600)
            letsencrypt_dir.mkdir(parents=True, exist_ok=True)
            if not acme_json_path.exists():
                acme_json_path.touch()
            acme_json_path.chmod(0o600)

            # Restart Traefik container
            self._restart_traefik()

            # Save config to database
            self._save_config(mode="domain", domain=domain, email=email)

            logger.info(f"Domain SSL configured for {domain!r}")
            return f"https://{domain}"

        except Exception as e:
            logger.error(f"Domain SSL setup failed: {e}")
            if backup is not None:
                try:
                    writer.restore_config(backup)
                    logger.info("Restored Traefik config from backup")
                except Exception as restore_err:
                    logger.error(f"Failed to restore Traefik config: {restore_err}")
            if isinstance(e, SSLSetupError):
                raise
            raise SSLSetupError(f"Domain SSL setup failed: {e}") from e

    def configure_ip_only_ssl(self) -> str:
        """Configure self-signed certificate SSL for IP-only access.

        Generates a self-signed certificate, writes Traefik config, and
        restarts Traefik. On failure, restores the previous Traefik config.

        Returns:
            Message describing the self-signed cert configuration.

        Raises:
            SSLSetupError: If configuration fails (backup is restored).
        """
        settings = get_settings()
        data_dir = Path(settings.data_dir)
        traefik_config_dir = data_dir / "traefik"
        certs_dir = data_dir / "certs"
        cert_path = certs_dir / "cert.pem"
        key_path = certs_dir / "key.pem"

        writer = TraefikConfigWriter(traefik_config_dir)
        backup = writer.backup_config()

        try:
            # Generate self-signed certificate
            generate_self_signed_cert(cert_path=cert_path, key_path=key_path)

            # Write new Traefik config for IP-only mode
            writer.write_ip_only_config()

            # Restart Traefik container
            self._restart_traefik()

            # Save config to database
            self._save_config(mode="ip_only", domain=None, email=None)

            logger.info("IP-only SSL configured with self-signed certificate")
            return (
                "SSL configured with self-signed certificate. "
                "Your browser will show a security warning - this is expected for IP-only access."
            )

        except Exception as e:
            logger.error(f"IP-only SSL setup failed: {e}")
            if backup is not None:
                try:
                    writer.restore_config(backup)
                    logger.info("Restored Traefik config from backup")
                except Exception as restore_err:
                    logger.error(f"Failed to restore Traefik config: {restore_err}")
            if isinstance(e, SSLSetupError):
                raise
            raise SSLSetupError(f"IP-only SSL setup failed: {e}") from e

    def _restart_traefik(self) -> None:
        """Restart the Traefik container via Docker socket.

        Raises:
            SSLSetupError: If the container is not found or restart fails.
        """
        try:
            client = docker.from_env()  # type: ignore[attr-defined]
            container = client.containers.get("hypertrader-traefik")
            container.restart(timeout=30)
            logger.info("Restarted hypertrader-traefik container")
        except docker.errors.NotFound as e:
            raise SSLSetupError("Traefik container not found: hypertrader-traefik") from e
        except docker.errors.APIError as e:
            raise SSLSetupError(f"Failed to restart Traefik container: {e}") from e

    def _save_config(
        self,
        mode: str,
        domain: str | None,
        email: str | None,
    ) -> None:
        """Persist SSL configuration to the database.

        Creates or updates the SSLConfig singleton (id=1).

        Args:
            mode: SSL mode - "domain" or "ip_only".
            domain: Domain name (for Let's Encrypt mode), or None.
            email: ACME email address (for Let's Encrypt mode), or None.
        """
        config = self.db.get(SSLConfig, 1)
        if config is None:
            config = SSLConfig(id=1)
            config.mode = mode
            config.domain = domain
            config.email = email
            config.configured_at = datetime.now(UTC)
            self.db.add(config)
        else:
            config.mode = mode
            config.domain = domain
            config.email = email
            config.configured_at = datetime.now(UTC)
        self.db.commit()
