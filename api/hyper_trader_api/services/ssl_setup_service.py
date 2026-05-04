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
        """Configure Let's Encrypt SSL for a domain (config + DB only).

        Writes Traefik config and persists DB row. Does NOT restart Traefik —
        the caller MUST schedule ``restart_traefik`` as a background task so the
        HTTP response can flush before Traefik stops listening (otherwise the
        browser fetch is severed mid-flight with NetworkError).

        On config-write failure, restores the previous Traefik config.

        Args:
            domain: The domain name for Let's Encrypt certificate.
            email: Email address for Let's Encrypt ACME registration.

        Returns:
            HTTPS redirect URL (https://<domain>).

        Raises:
            SSLSetupError: If configuration fails (backup is restored).
        """
        settings = get_settings()

        if settings.environment != "production":
            raise SSLSetupError("SSL setup is only available in production environment")

        traefik_config_dir = Path(settings.traefik_config_dir)

        writer = TraefikConfigWriter(traefik_config_dir)
        backup = writer.backup_config()

        try:
            # Write new Traefik config for domain mode
            writer.write_domain_config(
                domain,
                email,
                ca_server=settings.acme_ca_server,
            )

            # Save config to database
            self._save_config(mode="domain", domain=domain, email=email)

            logger.info(f"Domain SSL configured for {domain!r} (restart deferred)")
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

    def repair_if_inconsistent(self) -> None:
        """Detect and repair stale SSL config on startup.

        Called during application lifespan startup. If the DB records SSL as
        configured (mode='domain') but ``traefik.yml`` is missing or lacks a
        ``certificatesResolvers`` section, the Traefik config files are
        re-written from the stored domain/email and Traefik is restarted.

        This handles the reinstall scenario: ``rm -rf /opt/hyper-trader`` resets
        ``traefik.yml`` to the bootstrap template, but named volumes survive so
        the DB still shows ``ssl_configured=true``.

        Errors are logged but never raised — a startup failure here must not
        prevent the API from starting.
        """
        settings = get_settings()
        if settings.environment != "production":
            return

        config = self.get_ssl_config()
        if config is None or config.mode is None or not config.domain or not config.email:
            return

        traefik_config_dir = Path(settings.traefik_config_dir)
        traefik_path = traefik_config_dir / "traefik.yml"

        consistent = traefik_path.exists() and "certificatesResolvers" in traefik_path.read_text()
        if consistent:
            return

        logger.warning(
            "Stale SSL config detected — traefik.yml missing or has no certificatesResolvers. "
            "Re-writing from stored domain/email."
        )
        try:
            writer = TraefikConfigWriter(traefik_config_dir)
            writer.write_domain_config(
                config.domain,
                config.email,
                ca_server=settings.acme_ca_server,
            )
        except Exception as e:
            logger.error(f"SSL config repair failed (write): {e}")
            return

        self.restart_traefik()
        logger.info("SSL config repaired. Traefik restarted.")

    def restart_traefik(self) -> None:
        """Restart the Traefik container via Docker socket.

        Public so the SSL setup router can schedule it as a FastAPI BackgroundTask
        (runs after the HTTP response is flushed to the client).

        Errors are logged but not raised back to the caller, since by the time
        this runs the HTTP response is already sent. If the restart fails, the
        new Traefik config is still on disk and will be picked up on the next
        Traefik or stack restart.
        """
        try:
            client = docker.from_env()  # type: ignore[attr-defined]
            container = client.containers.get("hypertrader-traefik")
            container.restart(timeout=30)
            logger.info("Restarted hypertrader-traefik container")
        except docker.errors.NotFound:
            logger.error(
                "Traefik container not found: hypertrader-traefik. "
                "New config is on disk; restart Traefik manually to apply."
            )
        except docker.errors.APIError as e:
            logger.error(
                f"Failed to restart Traefik container: {e}. "
                "New config is on disk; restart Traefik manually to apply."
            )

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
