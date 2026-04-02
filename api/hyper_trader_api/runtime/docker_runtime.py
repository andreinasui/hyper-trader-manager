"""
Docker Swarm runtime implementation for trader lifecycle management.

Manages trader services using Docker Swarm with native secret management.
"""

from pathlib import Path
from typing import Any

from docker.errors import APIError, NotFound
from docker.types import (
    EndpointSpec,
    Mount,
    RestartPolicy,
    SecretReference,
    ServiceMode,
)

import docker


class DockerRuntime:
    """
    Docker Swarm-based implementation of trader runtime.

    Manages trader services with Docker secrets for private keys,
    proper network isolation, and config mounting.
    """

    NETWORK_NAME = "hyper-trader-internal"
    IMAGE_PREFIX = "hyper-trader"
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

    def create_trader(
        self,
        trader: Any,
        config_path: Path,
        private_key: str,
    ) -> None:
        """
        Create Docker secret and start a new trader service.

        Args:
            trader: Trader model with runtime_name, image_tag, wallet_address, id
            config_path: Path to JSON config file to mount
            private_key: Plain text private key to store as Docker secret

        Raises:
            APIError: If service with same name already exists
            OSError: If config file doesn't exist
        """
        # Ensure network exists
        self._ensure_network()

        # Verify config file exists
        if not config_path.exists():
            raise OSError(f"Config file not found: {config_path}")

        # Create Docker secret for private key
        secret_name = self._get_secret_name(trader.id)
        secret = self.client.secrets.create(
            name=secret_name,
            data=private_key.encode(),
            labels={"trader_id": trader.id, "managed_by": "hyper-trader-manager"},
        )

        # Build image name
        image = f"{self.IMAGE_PREFIX}:{trader.image_tag}"

        # Configure mounts
        mounts = [
            Mount(
                target="/app/config.json",
                source=str(config_path.absolute()),
                type="bind",
                read_only=True,
            ),
        ]

        # Create secret reference for the service
        secret_refs = [
            SecretReference(
                secret_id=secret.id,
                secret_name=secret_name,
                filename="private_key",
            ),
        ]

        # Create and start service
        self.client.services.create(
            image=image,
            name=trader.runtime_name,
            mode=ServiceMode("replicated", replicas=1),
            networks=[self.NETWORK_NAME],
            mounts=mounts,
            secrets=secret_refs,
            restart_policy=RestartPolicy(condition="any", max_attempts=0),
            endpoint_spec=EndpointSpec(mode="vip"),
            env=[f"WALLET_ADDRESS={trader.wallet_address}"],
        )

    def restart_trader(self, runtime_name: str) -> None:
        """
        Force update a trader service to trigger restart.

        Args:
            runtime_name: Service name

        Raises:
            NotFound: If service doesn't exist
        """
        service = self.client.services.get(runtime_name)
        service.force_update()

    def remove_trader(self, runtime_name: str, trader_id: str) -> None:
        """
        Stop service and remove associated Docker secret.

        Args:
            runtime_name: Service name to remove
            trader_id: Trader ID for secret lookup

        Raises:
            NotFound: If service doesn't exist
        """
        # Remove service first
        service = self.client.services.get(runtime_name)
        service.remove()

        # Remove the secret
        secret_name = self._get_secret_name(trader_id)
        try:
            secret = self.client.secrets.get(secret_name)
            secret.remove()
        except NotFound:
            # Secret already removed, that's fine
            pass

    def get_status(self, runtime_name: str) -> dict[str, Any]:
        """
        Get current status of a trader service.

        Args:
            runtime_name: Service name to check

        Returns:
            Status dict with state, running flag, and replica info
        """
        try:
            service = self.client.services.get(runtime_name)
            attrs = service.attrs

            # Get task info
            tasks = service.tasks()
            running_tasks = [t for t in tasks if t.get("Status", {}).get("State") == "running"]

            # Get replicas info
            spec = attrs.get("Spec", {})
            mode = spec.get("Mode", {})
            replicated = mode.get("Replicated", {})
            desired_replicas = replicated.get("Replicas", 1)

            status: dict[str, Any] = {
                "state": "running" if running_tasks else "pending",
                "running": len(running_tasks) > 0,
                "replicas": f"{len(running_tasks)}/{desired_replicas}",
            }

            # Add creation time if available
            if "CreatedAt" in attrs:
                status["started_at"] = attrs["CreatedAt"]

            return status

        except NotFound:
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
