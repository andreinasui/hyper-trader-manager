"""
Trader service for HyperTrader API.

Handles trader CRUD operations using direct Kubernetes API.
"""

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from hyper_trader_api.config import get_settings
from hyper_trader_api.models import Trader, TraderConfig, User
from hyper_trader_api.schemas.trader import TraderCreate, TraderUpdate
from hyper_trader_api.services.k8s_controller import (
    KubernetesControllerError,
    KubernetesTraderController,
)

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

    Uses KubernetesTraderController for direct K8s API operations
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
        self.k8s = None

        # Only initialize K8s controller if enabled
        if self.settings.k8s_enabled:
            try:
                self.k8s = KubernetesTraderController()
            except Exception as e:
                logger.warning(f"Failed to initialize K8s controller: {e}")
                # Continue without K8s support

    def _get_k8s_name(self, wallet_address: str) -> str:
        """Generate K8s resource name from wallet address."""
        short_address = wallet_address[2:10].lower()  # First 8 chars after 0x
        return f"trader-{short_address}"

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
            TraderServiceError: If K8s deployment fails
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

        k8s_name = self._get_k8s_name(trader_data.wallet_address)

        # Create trader in DB first
        trader = Trader(
            user_id=user.id,
            wallet_address=trader_data.wallet_address.lower(),
            k8s_name=k8s_name,
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

        # Flush to ensure trader has configs relationship populated
        self.db.flush()

        # Deploy to Kubernetes if enabled
        if self.settings.k8s_enabled and self.k8s:
            try:
                # Deploy to Kubernetes with privy_user_id
                self.k8s.deploy_trader(trader, user.privy_user_id)

                # Update status to running (reconciliation will sync actual state)
                trader.status = "running"
                self.db.commit()
                self.db.refresh(trader)

                return trader

            except KubernetesControllerError as e:
                # Mark as failed but keep in DB for troubleshooting
                trader.status = "failed"
                self.db.commit()
                logger.error(f"Failed to deploy trader {k8s_name}: {e}")
                raise TraderServiceError(f"Deployment failed: {e}") from e
        else:
            # K8s is disabled - save to DB only
            trader.status = "pending"
            self.db.commit()
            self.db.refresh(trader)
            logger.info(f"K8s disabled - trader {trader.id} saved to DB only (status: pending)")
            return trader

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
        trader = self.db.query(Trader).filter(Trader.id == trader_id).first()

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
            TraderServiceError: If K8s update fails
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
            self.db.query(TraderConfig).filter(TraderConfig.trader_id == trader_id).count()
        )

        # Create new config version
        new_config = TraderConfig(
            trader_id=trader.id,
            config_json=config,
            version=max_version + 1,
        )
        self.db.add(new_config)
        self.db.flush()  # Ensure new config is visible

        if self.settings.k8s_enabled and self.k8s:
            try:
                # Update ConfigMap and restart pod
                self.k8s.update_trader_config(trader)

                self.db.commit()
                self.db.refresh(trader)

                return trader

            except KubernetesControllerError as e:
                self.db.rollback()
                logger.error(f"Failed to update trader {trader.k8s_name}: {e}")
                raise TraderServiceError(f"Config update failed: {e}") from e
        else:
            # K8s disabled - update DB only
            self.db.commit()
            self.db.refresh(trader)
            logger.info(f"K8s disabled - trader {trader.id} config updated in DB only")
            return trader

    def delete_trader(self, trader_id: uuid.UUID, user_id: str) -> None:
        """
        Delete a trader.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If K8s deletion fails
        """
        trader = self.get_trader(trader_id, user_id)

        # Remove from Kubernetes if enabled
        if self.settings.k8s_enabled and self.k8s:
            try:
                self.k8s.remove_trader(trader)
            except KubernetesControllerError as e:
                logger.error(f"Failed to remove trader {trader.k8s_name} from K8s: {e}")
                raise TraderServiceError(f"Deletion failed: {e}") from e
        else:
            logger.info(f"K8s disabled - skipping K8s removal for trader {trader.id}")

        # Delete from DB
        self.db.delete(trader)
        self.db.commit()

    def restart_trader(self, trader_id: uuid.UUID, user_id: str) -> None:
        """
        Restart a trader's pod.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
            TraderServiceError: If restart fails or K8s is disabled
        """
        trader = self.get_trader(trader_id, user_id)

        if not self.settings.k8s_enabled or not self.k8s:
            raise TraderServiceError("Cannot restart trader - Kubernetes is disabled")

        try:
            self.k8s.restart_trader(trader)
        except KubernetesControllerError as e:
            logger.error(f"Failed to restart trader {trader.k8s_name}: {e}")
            raise TraderServiceError(f"Restart failed: {e}") from e

    def get_trader_status(self, trader_id: uuid.UUID, user_id: str) -> dict[str, Any]:
        """
        Get detailed Kubernetes status for a trader.

        Args:
            trader_id: Trader's UUID
            user_id: Owner's user ID

        Returns:
            Dict with trader info and K8s status

        Raises:
            TraderNotFoundError: If trader doesn't exist
            TraderOwnershipError: If user doesn't own trader
        """
        trader = self.get_trader(trader_id, user_id)

        k8s_status = {}

        if self.settings.k8s_enabled and self.k8s:
            try:
                k8s_status = self.k8s.get_trader_status(trader)
            except KubernetesControllerError as e:
                logger.warning(f"Failed to get K8s status for {trader.k8s_name}: {e}")
                k8s_status = {
                    "exists": False,
                    "pod_phase": "Unknown",
                    "ready": False,
                    "restarts": 0,
                    "pod_ip": None,
                    "node": None,
                    "started_at": None,
                    "error": str(e),
                }
        else:
            k8s_status = {
                "exists": False,
                "pod_phase": "K8s Disabled",
                "ready": False,
                "message": "Kubernetes integration is disabled",
            }

        return {
            "id": str(trader.id),
            "wallet_address": trader.wallet_address,
            "k8s_name": trader.k8s_name,
            "status": trader.status,
            "k8s_status": k8s_status,
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

        if not self.settings.k8s_enabled or not self.k8s:
            return "Logs unavailable - Kubernetes is disabled"

        try:
            logs = self.k8s.get_trader_logs(trader, tail_lines)
            return logs if logs else "No logs available"
        except KubernetesControllerError as e:
            logger.warning(f"Failed to get logs for {trader.k8s_name}: {e}")
            return f"Error retrieving logs: {e}"
