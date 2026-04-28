"""SSL setup orchestration service."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import docker
import docker.errors
from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.models.ssl_config import SSLConfig
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

        # Defense-in-depth: only allow SSL setup in production
        if settings.environment != "production":
            raise SSLSetupError("SSL setup is only available in production environment")

        traefik_config_dir = Path(settings.traefik_config_dir)

        writer = TraefikConfigWriter(traefik_config_dir)
        backup = writer.backup_config()

        try:
            # Write new Traefik config for domain mode
            writer.write_domain_config(domain, email)

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
            mode: SSL mode - "domain" (Let's Encrypt).
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
