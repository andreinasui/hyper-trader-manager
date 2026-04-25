"""
Trader service for HyperTrader API.

Handles trader CRUD operations using Docker runtime.
"""

import logging
import uuid

import yaml
from datetime import UTC
from typing import Any

from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.models import Trader, TraderConfig, User
from hyper_trader_api.runtime.factory import get_runtime
from hyper_trader_api.schemas.trader import TraderCreate, TraderInfoUpdate, TraderUpdate
from hyper_trader_api.services.image_service import ImageService

logger = logging.getLogger(__name__)


class TraderServiceError(Exception):
    """Base exception for trader service errors."""

    pass


class TraderNotFoundError(TraderServiceError):
    """Raised when trader is not found."""

    pass


class TraderOwnershipError(TraderServiceError):
    """Raised when user doesn't own the trader."""

    pass


class TraderService:
    """
    Service for managing traders.

    Uses Docker runtime for container lifecycle management
    while maintaining state in the database.
    """

    def __init__(self, db: Session):
        """
        Initialize trader service.

        Args:
            db: Database session
        """
        self.db = db
        self.settings = get_settings()
        self.runtime = get_runtime()

    def _validate_config(self, config: dict, wallet_address: str) -> None:
        """Validate config business rules."""
        # Check copy account is not same as self account
        copy_addr = (
            config.get("provider_settings", {}).get("copy_account", {}).get("address", "").lower()
        )
        if copy_addr == wallet_address.lower():
            raise ValueError("Copy account cannot be the same as self account")

        # Check allowed and blocked assets don't overlap
        risk = (
            config.get("trader_settings", {}).get("trading_strategy", {}).get("risk_parameters", {})
        )
        allowed = set(risk.get("allowed_assets") or [])
        blocked = set(risk.get("blocked_assets") or [])
        overlap = allowed & blocked
        if overlap:
            raise ValueError(f"Assets cannot be both allowed and blocked: {overlap}")

        # Check bucket config - only manual OR auto, not both
        bucket = config.get("trader_settings", {}).get("trading_strategy", {}).get("bucket_config")
        if bucket:
            has_manual = bucket.get("manual") is not None
            has_auto = bucket.get("auto") is not None
            if has_manual and has_auto:
                raise ValueError("Bucket config must use either manual or auto, not both")

    def _get_runtime_name(self, wallet_address: str) -> str:
        """Generate runtime container name from wallet address."""
        short_address = wallet_address[2:10].lower()  # First 8 chars after 0x
        return f"trader-{short_address}"

    def _get_config_data(self, trader_id: str) -> str:
        """
        Get trader's config from database as YAML string.

        Args:
            trader_id: Trader's UUID as string

        Returns:
            YAML config content as string

        Raises:
            TraderServiceError: If no config found in database
        """
        trader_config = (
            self.db.query(TraderConfig).filter(TraderConfig.trader_id == trader_id).first()
        )

        if not trader_config:
            raise TraderServiceError(f"No config found for trader {trader_id}")

        return yaml.safe_dump(trader_config.config_json, default_flow_style=False)

    def create_trader(self, user: User, trader_data: TraderCreate) -> Trader:
        """
        Create a new trader (config only, no container).

        Creates the trader record, config version, config file, and Docker secret.
        Does NOT start the container - use start_trader() for that.

        Args:
            user: Owner User object
            trader_data: Trader creation data

        Returns:
            Created Trader model with status "configured"

        Raises:
            ValueError: If wallet address already exists or config invalid
            TraderServiceError: If secret creation fails
        """
        # Check if wallet already exists
        existing = (
            self.db.query(Trader)
            .filter(Trader.wallet_address == trader_data.wallet_address.lower())
            .first()
        )
        if existing:
            raise ValueError(f"Trader already exists for wallet: {trader_data.wallet_address}")

        # Check name uniqueness if provided
        if trader_data.name:
            existing = (
                self.db.query(Trader)
                .filter(Trader.user_id == user.id, Trader.name == trader_data.name)
                .first()
            )
            if existing:
                raise ValueError(f"A trader with name '{trader_data.name}' already exists")

        # Ensure config has self_account.address matching wallet_address
        config = trader_data.config.model_dump()
        if "provider_settings" not in config:
            config["provider_settings"] = {}
        if "self_account" not in config["provider_settings"]:
            config["provider_settings"]["self_account"] = {}
        config["provider_settings"]["self_account"]["address"] = trader_data.wallet_address

        # Validate config business rules
        self._validate_config(config, trader_data.wallet_address)

        runtime_name = self._get_runtime_name(trader_data.wallet_address)

        # Determine image tag: use provided tag or fallback to latest remote, then latest local
        image_tag = getattr(trader_data, "image_tag", None)
        if not image_tag:
            version_info = ImageService().get_image_versions()
            image_tag = version_info.latest_remote or version_info.latest_local
            if not image_tag:
                raise TraderServiceError(
                    "No image available. No remote version found and no local image has been pulled."
                )

        # Create trader in DB
        trader = Trader(
            user_id=user.id,
            wallet_address=trader_data.wallet_address.lower(),
            runtime_name=runtime_name,
            status="configured",
            start_attempts=0,
            image_tag=image_tag,
            name=trader_data.name,
            description=trader_data.description,
        )
        self.db.add(trader)
        self.db.flush()

        # Create config version 1
        trader_config = TraderConfig(
            trader_id=trader.id,
            config_json=config,
            version=1,
        )
        self.db.add(trader_config)
        self.db.flush()

        # Create Docker secret (but don't start container)
        try:
            self.runtime.create_secret(trader.id, trader_data.private_key)
            self.db.commit()
            self.db.refresh(trader)
            logger.info(f"Trader configured: {runtime_name} for user {user.username}")
            return trader
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create secret for {runtime_name}: {e}")
            raise TraderServiceError(f"Secret creation failed: {e}") from e

    def start_trader(self, trader_id: uuid.UUID, user_id: str, max_attempts: int = 3) -> Trader:
        """
        Start a trader by creating its Docker Swarm service.

        Attempts to create the service up to max_attempts times with 2s delay between.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID
            max_attempts: Maximum retry attempts (default: 3)

        Returns:
            Updated Trader model

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            ValueError: If trader is not in a startable state
            TraderServiceError: If all start attempts fail
        """
        import time

        trader = self.get_trader(trader_id, user_id)

        # Validate trader is in a startable state
        startable_states = ("configured", "stopped", "failed")
        if trader.status not in startable_states:
            raise ValueError(
                f"Trader cannot be started from status '{trader.status}'. "
                f"Must be one of: {startable_states}"
            )

        # Check if service already exists (shouldn't happen, but be safe)
        if self.runtime.service_exists(trader.runtime_name):
            logger.warning(f"Service {trader.runtime_name} already exists, removing first")
            self.runtime.remove_service(trader.runtime_name)

        # Update status to starting
        trader.status = "starting"
        trader.start_attempts = 0
        trader.last_error = None
        self.db.commit()

        # Get config data from database as YAML string
        config_data = self._get_config_data(str(trader.id))
        last_error = None

        for attempt in range(1, max_attempts + 1):
            trader.start_attempts = attempt
            self.db.commit()

            try:
                self.runtime.create_service(trader, config_data)
                trader.status = "running"
                trader.last_error = None
                self.db.commit()
                self.db.refresh(trader)
                logger.info(f"Trader started: {trader.runtime_name} (attempt {attempt})")
                return trader

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Failed to start trader {trader.runtime_name} "
                    f"(attempt {attempt}/{max_attempts}): {e}"
                )
                if attempt < max_attempts:
                    time.sleep(2)

        # All attempts failed
        trader.status = "failed"
        trader.last_error = last_error
        self.db.commit()
        self.db.refresh(trader)
        logger.error(f"Trader failed to start after {max_attempts} attempts: {trader.runtime_name}")
        raise TraderServiceError(
            f"Failed to start trader after {max_attempts} attempts: {last_error}"
        )

    def stop_trader(self, trader_id: uuid.UUID, user_id: str) -> Trader:
        """
        Stop a trader by removing its Docker Swarm service.

        Keeps the Docker secret and DB record for later restart.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Returns:
            Updated Trader model

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            ValueError: If trader is not in a stoppable state
            TraderServiceError: If stop fails
        """
        from datetime import datetime

        trader = self.get_trader(trader_id, user_id)

        # Validate trader is in a stoppable state
        stoppable_states = ("running", "starting", "failed")
        if trader.status not in stoppable_states:
            raise ValueError(
                f"Trader cannot be stopped from status '{trader.status}'. "
                f"Must be one of: {stoppable_states}"
            )

        try:
            # Remove service only (keep secret)
            if self.runtime.service_exists(trader.runtime_name):
                self.runtime.remove_service(trader.runtime_name)

            trader.status = "stopped"
            trader.stopped_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(trader)
            logger.info(f"Trader stopped: {trader.runtime_name}")
            return trader

        except Exception as e:
            logger.error(f"Failed to stop trader {trader.runtime_name}: {e}")
            raise TraderServiceError(f"Failed to stop trader: {e}") from e

    def list_traders(self, user_id: str) -> list[Trader]:
        """
        List all traders owned by a user.

        Args:
            user_id: Owner's user ID

        Returns:
            List of Trader models
        """
        return self.db.query(Trader).filter(Trader.user_id == user_id).all()

    def get_trader(self, trader_id: uuid.UUID, user_id: str) -> Trader:
        """
        Get a trader by ID, validating ownership.

        Args:
            trader_id: Trader's UUID
            user_id: Expected owner's user ID

        Returns:
            Trader model

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
        """
        trader = self.db.query(Trader).filter(Trader.id == str(trader_id)).first()

        if not trader:
            raise TraderNotFoundError(f"Trader not found: {trader_id}")

        if trader.user_id != user_id:
            raise TraderOwnershipError(f"User {user_id} does not own trader {trader_id}")

        return trader

    def update_trader(
        self, trader_id: uuid.UUID, user_id: str, update_data: TraderUpdate
    ) -> Trader:
        """
        Update a trader's configuration.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID
            update_data: Update data

        Returns:
            Updated Trader model

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If update fails
        """
        trader = self.get_trader(trader_id, user_id)

        if update_data.config is None:
            return trader  # Nothing to update

        # Ensure config has correct self_account.address (auto-fill from trader's wallet_address)
        config = update_data.config.model_dump()
        if "provider_settings" not in config:
            config["provider_settings"] = {}
        if "self_account" not in config["provider_settings"]:
            config["provider_settings"]["self_account"] = {}
        config["provider_settings"]["self_account"]["address"] = trader.wallet_address

        # Validate config business rules
        self._validate_config(config, trader.wallet_address)

        # Find existing config and update it
        existing_config = (
            self.db.query(TraderConfig).filter(TraderConfig.trader_id == str(trader_id)).first()
        )

        if existing_config:
            existing_config.config_json = config
        else:
            # Create new config if none exists
            new_config = TraderConfig(
                trader_id=trader.id,
                config_json=config,
                version=1,
            )
            self.db.add(new_config)

        self.db.flush()  # Ensure config changes are visible

        # Commit database changes (service restart is handled separately via restart endpoint)
        self.db.commit()
        self.db.refresh(trader)
        logger.info(f"Trader config updated: {trader.runtime_name}")
        return trader

    def update_trader_info(
        self,
        trader_id: uuid.UUID,
        user_id: str,
        update_data: TraderInfoUpdate,
    ) -> Trader:
        """
        Update trader display info (name/description).

        Does NOT restart the container - this is metadata only.

        Args:
            trader_id: UUID of the trader to update
            user_id: ID of the requesting user
            update_data: New name and/or description

        Returns:
            Updated Trader instance

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own the trader
            ValueError: If name already exists for this user
        """
        trader = self.get_trader(trader_id, user_id)

        # Check name uniqueness if name is being set
        if update_data.name is not None:
            existing = (
                self.db.query(Trader)
                .filter(
                    Trader.user_id == user_id,
                    Trader.name == update_data.name,
                    Trader.id != str(trader_id),
                )
                .first()
            )
            if existing:
                raise ValueError(f"A trader with name '{update_data.name}' already exists")

        # Update fields if provided (Pydantic ensures valid non-empty strings)
        if update_data.name is not None:
            trader.name = update_data.name
        if update_data.description is not None:
            trader.description = update_data.description

        self.db.commit()
        self.db.refresh(trader)
        logger.info(f"Trader info updated: {trader.runtime_name}")
        return trader

    def delete_trader(self, trader_id: uuid.UUID, user_id: str) -> None:
        """
        Delete a trader completely.

        Removes Docker service, secret, config file, and all DB records.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If deletion fails
        """
        trader = self.get_trader(trader_id, user_id)

        # Remove from Docker runtime (service + secret + config)
        try:
            self.runtime.remove_service(trader.runtime_name, True, trader.id)
        except Exception as e:
            logger.error(f"Failed to remove trader {trader.runtime_name} from runtime: {e}")
            raise TraderServiceError(f"Service deletion failed: {e}") from e

        # Delete from DB (cascade will delete configs)
        self.db.delete(trader)
        self.db.commit()

        logger.info(f"Trader deleted: {trader.runtime_name}")

    def restart_trader(self, trader_id: uuid.UUID, user_id: str) -> Trader:
        """
        Restart a trader by stopping and starting with fresh config from DB.

        This ensures the running trader always uses the latest configuration
        stored in the database, not a stale Docker Config object.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Returns:
            Updated Trader model

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If restart fails
        """
        trader = self.get_trader(trader_id, user_id)

        # Stop the running service (keep secret + DB records)
        try:
            if self.runtime.service_exists(trader.runtime_name):
                self.runtime.remove_service(trader.runtime_name)
                logger.info(f"Stopped trader service for restart: {trader.runtime_name}")
        except Exception as e:
            logger.error(f"Failed to stop trader for restart {trader.runtime_name}: {e}")
            raise TraderServiceError(f"Restart failed during stop: {e}") from e

        # Mark as stopped so start_trader() accepts it
        trader.status = "stopped"
        self.db.commit()

        # Start with fresh config from DB (reads config_json, creates new Docker Config)
        return self.start_trader(trader_id, user_id)

    def get_trader_status(self, trader_id: uuid.UUID, user_id: str) -> dict[str, Any]:
        """
        Get detailed runtime status for a trader.

        If the service has crashed 3+ times, auto-stops it and marks as failed.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Returns:
            Dict with trader info and runtime status

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
        """
        trader = self.get_trader(trader_id, user_id)

        try:
            runtime_status = self.runtime.get_status(trader.runtime_name)
        except Exception as e:
            logger.warning(f"Failed to get runtime status for {trader.runtime_name}: {e}")
            runtime_status = {
                "state": "unknown",
                "running": False,
                "error": str(e),
            }

        # Auto-stop after 3 crash restarts
        restart_count = runtime_status.get("restart_count", 0)
        if runtime_status.get("state") == "restarting" and restart_count >= 3:
            logger.warning(
                f"Trader {trader.runtime_name} crashed {restart_count} times, auto-stopping"
            )
            error_msg = runtime_status.get("error", "Container crashed repeatedly")
            self._auto_stop_failed_trader(trader, error_msg)
            # Update runtime_status to reflect the stop
            runtime_status["state"] = "failed"
            runtime_status["running"] = False

        return {
            "id": trader.id,
            "wallet_address": trader.wallet_address,
            "runtime_name": trader.runtime_name,
            "status": trader.status,
            "runtime_status": runtime_status,
        }

    def _auto_stop_failed_trader(self, trader: Trader, error_msg: str) -> None:
        """
        Stop a repeatedly crashing trader and mark as failed.

        Args:
            trader: Trader model
            error_msg: Error message from last crash
        """
        from datetime import datetime

        try:
            if self.runtime.service_exists(trader.runtime_name):
                self.runtime.remove_service(trader.runtime_name)

            trader.status = "failed"
            trader.last_error = error_msg
            trader.stopped_at = datetime.now(UTC)
            self.db.commit()
            self.db.refresh(trader)
            logger.info(f"Auto-stopped failed trader {trader.runtime_name}: {error_msg}")
        except Exception as e:
            logger.error(f"Failed to auto-stop trader {trader.runtime_name}: {e}")

    def get_trader_logs(self, trader_id: uuid.UUID, user_id: str, tail_lines: int = 100) -> str:
        """
        Get logs for a trader.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID
            tail_lines: Number of log lines to return

        Returns:
            Log output as string

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
        """
        trader = self.get_trader(trader_id, user_id)

        try:
            logs = self.runtime.get_logs(trader.runtime_name, tail_lines)
            return logs if logs else "No logs available"
        except Exception as e:
            logger.warning(f"Failed to get logs for {trader.runtime_name}: {e}")
            return f"Error retrieving logs: {e}"

    def update_image(self, trader_id: uuid.UUID, user_id: str, new_tag: str) -> Trader:
        """
        Update a trader's Docker image to a new tag.

        Pulls the image first (regardless of trader status), then updates
        the Swarm service if running, and always updates the DB record.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID
            new_tag: New image tag to use (e.g. "0.4.4")

        Returns:
            Updated Trader model with new image_tag

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If image pull or service update fails
        """
        trader = self.get_trader(trader_id, user_id)

        # Pull image first (always, regardless of trader status)
        try:
            self.runtime.pull_image(new_tag)
        except Exception as e:
            logger.error(f"Failed to pull image tag {new_tag}: {e}")
            raise TraderServiceError(f"Failed to pull image '{new_tag}': {e}") from e

        # Update running service if applicable
        if trader.status == "running":
            try:
                self.runtime.update_service_image(trader.runtime_name, new_tag)
            except Exception as e:
                logger.error(f"Failed to update service image for {trader.runtime_name}: {e}")
                raise TraderServiceError(f"Failed to update service image: {e}") from e

        # Always update DB
        trader.image_tag = new_tag
        self.db.commit()
        self.db.refresh(trader)
        logger.info(f"Trader image updated: {trader.runtime_name} → {new_tag}")
        return trader
