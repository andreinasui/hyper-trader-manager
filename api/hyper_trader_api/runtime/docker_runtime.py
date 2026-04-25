"""
Docker Swarm runtime implementation for trader lifecycle management.

Manages trader services using Docker Swarm with native secret management.
"""

import logging
import re
from typing import Any

import docker
from docker.errors import APIError, NotFound
from docker.types import (
    ConfigReference,
    EndpointSpec,
    RestartPolicy,
    SecretReference,
    ServiceMode,
    UpdateConfig,
)

logger = logging.getLogger(__name__)


class DockerRuntime:
    """
    Docker Swarm-based implementation of trader runtime.

    Manages trader services with Docker secrets for private keys,
    proper network isolation, and config mounting.
    """

    NETWORK_NAME = "hyper-trader-internal"
    IMAGE_PREFIX = "ghcr.io/andreinasui/hyper-trader"
    SECRET_PREFIX = "ht"

    def __init__(self, client: docker.DockerClient | None = None):
        """
        Initialize Docker runtime.

        Args:
            client: Docker client instance. If None, creates from environment.
        """
        self.client = client or docker.from_env()
        self._ensure_swarm()

    def _ensure_swarm(self) -> None:
        """
        Ensure Docker is in Swarm mode, initialize if needed.

        Single-node swarm is sufficient for secret management.
        """
        try:
            self.client.swarm.attrs["ID"]
        except (APIError, KeyError):
            # Not in swarm mode, initialize
            self.client.swarm.init()

    def _ensure_network(self) -> None:
        """
        Ensure the internal overlay network exists for swarm services.

        Creates an overlay network for trader services to communicate
        securely without exposing ports to the host.
        """
        try:
            self.client.networks.get(self.NETWORK_NAME)
        except NotFound:
            self.client.networks.create(
                self.NETWORK_NAME,
                driver="overlay",
                attachable=True,
            )

    def _get_secret_name(self, trader_id: str) -> str:
        """Generate secret name from trader ID."""
        return f"{self.SECRET_PREFIX}_{trader_id}_private_key"

    def create_secret(self, trader_id: str, private_key: str) -> str:
        """
        Create Docker secret for trader private key.

        Args:
            trader_id: Trader ID for secret naming
            private_key: Plain text private key

        Returns:
            Secret name

        Raises:
            APIError: If secret creation fails
        """
        secret_name = self._get_secret_name(trader_id)

        # Check if secret already exists
        try:
            self.client.secrets.get(secret_name)
            return secret_name  # Already exists
        except NotFound:
            pass

        self.client.secrets.create(
            name=secret_name,
            data=private_key.encode(),
            labels={"trader_id": trader_id, "managed_by": "hyper-trader-manager"},
        )
        return secret_name

    def _get_config_name(self, trader_id: str) -> str:
        """Generate Docker config name from trader ID."""
        return f"{self.SECRET_PREFIX}_{trader_id}_config"

    def create_config(self, trader_id: str, config_data: str) -> str:
        """
        Create Docker config for trader configuration.

        Args:
            trader_id: Trader ID for config naming
            config_data: YAML config content as string

        Returns:
            Config name

        Raises:
            APIError: If config creation fails
        """
        config_name = self._get_config_name(trader_id)

        # Remove existing config if present (configs are immutable, must recreate)
        try:
            existing = self.client.configs.get(config_name)
            existing.remove()
            logger.debug(f"Removed existing config {config_name} for update")
        except NotFound:
            pass

        self.client.configs.create(
            name=config_name,
            data=config_data.encode(),
            labels={"trader_id": trader_id, "managed_by": "hyper-trader-manager"},
        )
        logger.debug(f"Created Docker config {config_name}")
        return config_name

    def remove_config(self, trader_id: str) -> None:
        """
        Remove Docker config for a trader.

        Args:
            trader_id: Trader ID for config lookup
        """
        config_name = self._get_config_name(trader_id)
        try:
            config = self.client.configs.get(config_name)
            config.remove()
            logger.debug(f"Removed config {config_name}")
        except NotFound:
            logger.debug(f"Config {config_name} not found (already removed)")

    def create_service(
        self,
        trader: Any,
        config_data: str,
    ) -> None:
        """
        Create Docker Swarm service for trader (secret must exist).

        Args:
            trader: Trader model with runtime_name, image_tag, wallet_address, id
            config_data: YAML config content as string

        Raises:
            APIError: If service creation fails
            NotFound: If secret doesn't exist
        """
        self._ensure_network()

        # Get existing secret
        secret_name = self._get_secret_name(trader.id)
        secret = self.client.secrets.get(secret_name)

        # Create Docker config for trader configuration
        config_name = self.create_config(str(trader.id), config_data)
        config = self.client.configs.get(config_name)

        image = f"{self.IMAGE_PREFIX}:{trader.image_tag}"

        secret_refs = [
            SecretReference(
                secret_id=secret.id,
                secret_name=secret_name,
                filename="private_key",
            ),
        ]

        config_refs = [
            ConfigReference(
                config_id=config.id,
                config_name=config_name,
                filename="/app/config.yaml",
            ),
        ]

        self.client.services.create(
            image=image,
            name=trader.runtime_name,
            mode=ServiceMode("replicated", replicas=1),
            networks=[self.NETWORK_NAME],
            secrets=secret_refs,
            configs=config_refs,
            restart_policy=RestartPolicy(condition="any", max_attempts=0),
            update_config=UpdateConfig(order="stop-first"),
            endpoint_spec=EndpointSpec(mode="vip"),
            env=[
                f"WALLET_ADDRESS={trader.wallet_address}",
                "CONFIG_PATH=/app/config.yaml",
                "PRIVATE_KEY_FILE=/run/secrets/private_key",
                "LOG_FORMAT=json",
                "LOG_LEVEL=debug",
            ],
        )

    def remove_service(
        self, runtime_name: str, remove_secret: bool = False, trader_id: str = ""
    ) -> None:
        """
        Stop service and optionally remove associated Docker secret and config.

        Args:
            runtime_name: Service name to remove
            remove_secret: Whether to also remove the Docker secret and config (default: True)
            trader_id: Trader ID for secret/config lookup

        Raises:
            NotFound: If service doesn't exist
        """
        logger.info(f"Removing trader service {runtime_name}")

        # Remove service first (may not exist if never started)
        try:
            service = self.client.services.get(runtime_name)
            service.remove()
            logger.info(f"Removed service {runtime_name}")
        except NotFound:
            logger.debug(f"Service {runtime_name} not found (already removed)")

        # Remove the secret and config if requested
        if remove_secret:
            # Remove config
            self.remove_config(trader_id)

            # Remove secret
            secret_name = self._get_secret_name(trader_id)
            try:
                secret = self.client.secrets.get(secret_name)
                secret.remove()
                logger.debug(f"Removed secret {secret_name}")
            except NotFound:
                logger.debug(f"Secret {secret_name} not found (already removed)")

    def get_status(self, runtime_name: str) -> dict[str, Any]:
        """
        Get current status of a trader service.

        Args:
            runtime_name: Service name to check

        Returns:
            Status dict with state, running flag, replica info, and error if any
        """
        try:
            service = self.client.services.get(runtime_name)
            attrs = service.attrs

            # Get task info - sorted by creation time (most recent first)
            tasks = service.tasks()
            tasks_sorted = sorted(
                tasks,
                key=lambda t: t.get("CreatedAt", ""),
                reverse=True,
            )

            # Get replicas info
            spec = attrs.get("Spec", {})
            mode = spec.get("Mode", {})
            replicated = mode.get("Replicated", {})
            desired_replicas = replicated.get("Replicas", 1)

            running_tasks = [t for t in tasks if t.get("Status", {}).get("State") == "running"]
            failed_tasks = [t for t in tasks if t.get("Status", {}).get("State") == "failed"]

            # Log all task states for debugging (exclude shutdown/complete noise)
            if tasks_sorted:
                task_states = [
                    f"{t.get('ID', 'unknown')[:12]}:{t.get('Status', {}).get('State', 'unknown')}"
                    for t in tasks_sorted[:5]  # Log up to 5 most recent
                    if t.get("Status", {}).get("State") not in ("shutdown", "complete")
                ]
                if task_states:
                    logger.debug(f"Service {runtime_name} tasks: {task_states}")

            # Determine state from the most recent task
            state = "pending"
            error_message = None

            if running_tasks:
                # Check for restart loop: running task + recent failures
                if failed_tasks:
                    state = "restarting"
                    # Get error from most recent failed task
                    recent_failed = max(
                        failed_tasks,
                        key=lambda t: t.get("CreatedAt", ""),
                    )
                    failed_status = recent_failed.get("Status", {})
                    error_message = (
                        failed_status.get("Err")
                        or failed_status.get("Message")
                        or "Container keeps crashing"
                    )
                    logger.warning(
                        f"Service {runtime_name}: restart loop detected "
                        f"({len(failed_tasks)} failures) - {error_message}"
                    )
                else:
                    state = "running"
                    logger.debug(f"Service {runtime_name}: running ({len(running_tasks)} tasks)")
            elif tasks_sorted:
                # Check the most recent task's state
                most_recent_task = tasks_sorted[0]
                task_status = most_recent_task.get("Status", {})
                task_state = task_status.get("State", "")

                # Log full task status for debugging failed states
                if task_state in ("failed", "rejected", "shutdown"):
                    logger.debug(f"Service {runtime_name} most recent task status: {task_status}")

                # Map Docker Swarm task states to app states
                # Swarm states: new, pending, assigned, accepted, preparing, ready,
                #               starting, running, complete, shutdown, failed, rejected, orphaned
                if task_state in ("failed", "rejected"):
                    state = "failed"
                    # Extract error message - Docker uses both "Err" and "Message"
                    error_message = (
                        task_status.get("Err")
                        or task_status.get("Message")
                        or task_status.get("Error")
                        or f"Task {task_state}"
                    )
                    logger.warning(f"Service {runtime_name}: task {task_state} - {error_message}")
                elif task_state in ("shutdown", "complete"):
                    state = "stopped"
                    logger.info(f"Service {runtime_name}: task {task_state}")
                elif task_state == "orphaned":
                    state = "error"
                    error_message = "Task is orphaned - node may be down"
                    logger.error(f"Service {runtime_name}: task orphaned")
                else:
                    # Preparing/starting states remain as "pending"
                    logger.debug(
                        f"Service {runtime_name}: task state={task_state}, mapped to pending"
                    )

            status: dict[str, Any] = {
                "state": state,
                "running": len(running_tasks) > 0,
                "replicas": f"{len(running_tasks)}/{desired_replicas}",
                "restart_count": len(failed_tasks),
            }

            # Add error message if available
            if error_message:
                status["error"] = error_message

            # Add creation time if available
            if "CreatedAt" in attrs:
                status["started_at"] = attrs["CreatedAt"]

            logger.info(
                f"Service {runtime_name} status: state={state}, "
                f"replicas={status['replicas']}"
                + (f", error={error_message}" if error_message else "")
            )

            return status

        except NotFound:
            logger.warning(f"Service {runtime_name}: not found in swarm")
            return {
                "state": "not_found",
                "running": False,
            }

    def get_logs(self, runtime_name: str, tail_lines: int) -> str:
        """
        Get recent logs from a trader service.

        Args:
            runtime_name: Service name
            tail_lines: Number of recent lines to retrieve

        Returns:
            Log output as string, empty if service not found
        """
        try:
            service = self.client.services.get(runtime_name)
            # Service logs returns a generator
            logs_gen = service.logs(stdout=True, stderr=True, tail=tail_lines)
            # Collect and decode logs
            logs_bytes = b"".join(logs_gen)
            return logs_bytes.decode("utf-8")
        except NotFound:
            return ""

    def service_exists(self, runtime_name: str) -> bool:
        """
        Check if a Docker Swarm service exists.

        Args:
            runtime_name: Service name to check

        Returns:
            True if service exists, False otherwise
        """
        try:
            self.client.services.get(runtime_name)
            return True
        except NotFound:
            return False

    def list_local_image_tags(self) -> list[str]:
        """
        List locally available image tags for ghcr.io/andreinasui/hyper-trader,
        sorted descending by semver (newest first).

        Returns:
            List of tag strings like ["0.4.4", "0.4.3"], newest first.
            Empty list if no matching images found.
        """
        semver_re = re.compile(r"^\d+\.\d+\.\d+$")
        tags = []
        try:
            images = self.client.images.list(name=self.IMAGE_PREFIX)
            for image in images:
                for tag in image.tags or []:
                    # tag is like "ghcr.io/andreinasui/hyper-trader:0.4.4"
                    parts = tag.split(":")
                    if len(parts) == 2 and semver_re.match(parts[1]):
                        tags.append(parts[1])
        except Exception:
            return []

        def semver_key(t: str) -> tuple[int, int, int]:
            a, b, c = t.split(".")
            return (int(a), int(b), int(c))

        return sorted(tags, key=semver_key, reverse=True)

    def pull_image(self, tag: str) -> None:
        """
        Pull a specific image tag from the registry.

        Args:
            tag: Image tag to pull (e.g. "0.4.4")

        Raises:
            docker.errors.APIError: If pull fails (e.g. auth error, tag not found)
        """
        self.client.images.pull(self.IMAGE_PREFIX, tag=tag)

    def update_service_image(self, runtime_name: str, new_tag: str) -> None:
        """
        Update a running Swarm service to use a new image tag.

        Args:
            runtime_name: Docker Swarm service name
            new_tag: New image tag (e.g. "0.4.4")

        Raises:
            NotFound: If service doesn't exist
            docker.errors.APIError: If update fails
        """
        service = self.client.services.get(runtime_name)
        new_image = f"{self.IMAGE_PREFIX}:{new_tag}"
        service.update(image=new_image, update_config=UpdateConfig(order="stop-first"))
