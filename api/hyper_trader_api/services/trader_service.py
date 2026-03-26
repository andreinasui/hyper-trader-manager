"""
Trader service for HyperTrader API.

Handles trader CRUD operations using Docker runtime for self-hosted deployment.
"""

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.models import Trader, TraderConfig, TraderSecret, User
from hyper_trader_api.runtime.factory import get_runtime
from hyper_trader_api.schemas.trader import TraderCreate, TraderUpdate
from hyper_trader_api.utils.crypto import decrypt_secret, encrypt_secret

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

        # Ensure data directory exists for trader configs
        self.config_dir = Path("./data/trader_configs")
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _get_runtime_name(self, wallet_address: str) -> str:
        """Generate runtime container name from wallet address."""
        short_address = wallet_address[2:10].lower()  # First 8 chars after 0x
        return f"trader-{short_address}"

    def _get_config_path(self, trader_id: str) -> Path:
        """Get path to trader's config file."""
        return self.config_dir / f"{trader_id}.json"

    def _write_config_file(self, trader: Trader) -> Path:
        """Write trader's latest config to a JSON file."""
        config_path = self._get_config_path(str(trader.id))

        if not trader.latest_config:
            raise TraderServiceError(f"Trader {trader.id} has no config")

        with open(config_path, "w") as f:
            json.dump(trader.latest_config.config_json, f, indent=2)

        return config_path

    def create_trader(self, user: User, trader_data: TraderCreate) -> Trader:
        """
        Create a new trader.

        Args:
            user: Owner User object
            trader_data: Trader creation data

        Returns:
            Created Trader model

        Raises:
            ValueError: If wallet address already exists
            TraderServiceError: If container deployment fails
        """
        # Check if wallet already exists
        existing = (
            self.db.query(Trader)
            .filter(Trader.wallet_address == trader_data.wallet_address.lower())
            .first()
        )
        if existing:
            raise ValueError(f"Trader already exists for wallet: {trader_data.wallet_address}")

        # Ensure config has self_account.address matching wallet_address
        config = trader_data.config.copy()
        if "self_account" not in config:
            config["self_account"] = {}
        config["self_account"]["address"] = trader_data.wallet_address

        runtime_name = self._get_runtime_name(trader_data.wallet_address)

        # Create trader in DB first
        trader = Trader(
            user_id=user.id,
            wallet_address=trader_data.wallet_address.lower(),
            runtime_name=runtime_name,
            status="pending",
            image_tag=self.settings.image_tag,
        )
        self.db.add(trader)
        self.db.flush()  # Get the ID without committing

        # Create config version 1
        trader_config = TraderConfig(
            trader_id=trader.id,
            config_json=config,
            version=1,
        )
        self.db.add(trader_config)

        # Encrypt and store private key
        try:
            encrypted_key = encrypt_secret(trader_data.private_key, self.settings.encryption_key)
            trader_secret = TraderSecret(
                trader_id=trader.id,
                private_key_encrypted=encrypted_key,
            )
            self.db.add(trader_secret)
        except ValueError as e:
            self.db.rollback()
            raise TraderServiceError(f"Failed to encrypt private key: {e}") from e

        # Flush to ensure trader has configs and secret populated
        self.db.flush()

        # Write config file
        try:
            config_path = self._write_config_file(trader)
        except Exception as e:
            self.db.rollback()
            raise TraderServiceError(f"Failed to write config file: {e}") from e

        # Deploy to Docker runtime
        try:
            # Decrypt private key for container environment
            decrypted_key = decrypt_secret(encrypted_key, self.settings.encryption_key)

            secret_env = {
                "PRIVATE_KEY": decrypted_key,
                "WALLET_ADDRESS": trader.wallet_address,
            }

            self.runtime.create_trader(trader, config_path, secret_env)

            # Update status to running
            trader.status = "running"
            self.db.commit()
            self.db.refresh(trader)

            logger.info(f"Trader created: {runtime_name} for user {user.username}")
            return trader

        except Exception as e:
            # Mark as failed but keep in DB for troubleshooting
            trader.status = "failed"
            self.db.commit()
            logger.error(f"Failed to deploy trader {runtime_name}: {e}")
            raise TraderServiceError(f"Container deployment failed: {e}") from e

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

        # Ensure config has correct address
        config = update_data.config.copy()
        if "self_account" not in config:
            config["self_account"] = {}
        config["self_account"]["address"] = trader.wallet_address

        # Get current max version
        max_version = (
            self.db.query(TraderConfig).filter(TraderConfig.trader_id == str(trader_id)).count()
        )

        # Create new config version
        new_config = TraderConfig(
            trader_id=trader.id,
            config_json=config,
            version=max_version + 1,
        )
        self.db.add(new_config)
        self.db.flush()  # Ensure new config is visible

        # Write updated config file
        try:
            self._write_config_file(trader)
        except Exception as e:
            self.db.rollback()
            raise TraderServiceError(f"Failed to write config file: {e}") from e

        # Restart container to pick up new config
        try:
            self.runtime.restart_trader(trader.runtime_name)
            self.db.commit()
            self.db.refresh(trader)
            logger.info(f"Trader updated and restarted: {trader.runtime_name}")
            return trader

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to restart trader {trader.runtime_name}: {e}")
            raise TraderServiceError(f"Config update failed: {e}") from e

    def delete_trader(self, trader_id: uuid.UUID, user_id: str) -> None:
        """
        Delete a trader.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If deletion fails
        """
        trader = self.get_trader(trader_id, user_id)

        # Remove from Docker runtime
        try:
            self.runtime.remove_trader(trader.runtime_name)
        except Exception as e:
            logger.error(f"Failed to remove trader {trader.runtime_name} from runtime: {e}")
            raise TraderServiceError(f"Container deletion failed: {e}") from e

        # Delete config file
        config_path = self._get_config_path(str(trader.id))
        if config_path.exists():
            config_path.unlink()

        # Delete from DB (cascade will delete configs and secret)
        self.db.delete(trader)
        self.db.commit()

        logger.info(f"Trader deleted: {trader.runtime_name}")

    def restart_trader(self, trader_id: uuid.UUID, user_id: str) -> None:
        """
        Restart a trader's container.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If restart fails
        """
        trader = self.get_trader(trader_id, user_id)

        try:
            self.runtime.restart_trader(trader.runtime_name)
            logger.info(f"Trader restarted: {trader.runtime_name}")
        except Exception as e:
            logger.error(f"Failed to restart trader {trader.runtime_name}: {e}")
            raise TraderServiceError(f"Restart failed: {e}") from e

    def get_trader_status(self, trader_id: uuid.UUID, user_id: str) -> dict[str, Any]:
        """
        Get detailed runtime status for a trader.

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

        return {
            "id": trader.id,
            "wallet_address": trader.wallet_address,
            "runtime_name": trader.runtime_name,
            "status": trader.status,
            "runtime_status": runtime_status,
        }

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
