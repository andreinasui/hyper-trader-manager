"""
Docker runtime implementation for trader lifecycle management.

Manages trader containers using Docker SDK, including network setup,
volume mounting, and container lifecycle operations.
"""

from pathlib import Path
from typing import Any

from docker.errors import NotFound

import docker


class DockerRuntime:
    """
    Docker-based implementation of trader runtime.

    Manages trader containers with proper network isolation, config mounting,
    and secret environment variable injection.
    """

    NETWORK_NAME = "hyper-trader-internal"
    IMAGE_PREFIX = "hyper-trader"

    def __init__(self, client: docker.DockerClient | None = None):
        """
        Initialize Docker runtime.

        Args:
            client: Docker client instance. If None, creates from environment.
        """
        self.client = client or docker.from_env()

    def create_trader(
        self,
        trader: Any,  # Trader model instance
        config_path: Path,
        secret_env: dict[str, str],
    ) -> None:
        """
        Create and start a new trader container.

        Creates the internal network if needed, then starts a detached container
        with proper restart policy, config mount, and environment variables.

        Args:
            trader: Trader model with runtime_name, image_tag, wallet_address
            config_path: Path to JSON config file to mount
            secret_env: Environment variables for secrets

        Raises:
            APIError: If container with same name already exists
            OSError: If config file doesn't exist
        """
        # Ensure network exists
        self._ensure_network()

        # Verify config file exists
        if not config_path.exists():
            raise OSError(f"Config file not found: {config_path}")

        # Build image name
        image = f"{self.IMAGE_PREFIX}:{trader.image_tag}"

        # Configure volume mount for config
        volumes = {
            str(config_path.absolute()): {
                "bind": "/app/config.json",
                "mode": "ro",
            }
        }

        # Create and start container
        self.client.containers.run(
            image,
            name=trader.runtime_name,
            detach=True,
            network=self.NETWORK_NAME,
            restart_policy={"Name": "unless-stopped"},
            environment=secret_env,
            volumes=volumes,
        )

    def restart_trader(self, runtime_name: str) -> None:
        """
        Restart an existing trader container.

        Args:
            runtime_name: Container name

        Raises:
            NotFound: If container doesn't exist
        """
        container = self.client.containers.get(runtime_name)
        container.restart()

    def remove_trader(self, runtime_name: str) -> None:
        """
        Stop and remove a trader container.

        Args:
            runtime_name: Container name

        Raises:
            NotFound: If container doesn't exist
        """
        container = self.client.containers.get(runtime_name)
        container.stop()
        container.remove()

    def get_status(self, runtime_name: str) -> dict[str, Any]:
        """
        Get current status of a trader container.

        Args:
            runtime_name: Container name

        Returns:
            Status dict with state, running flag, and additional info
        """
        try:
            container = self.client.containers.get(runtime_name)
            state = container.attrs["State"]

            status: dict[str, Any] = {
                "state": state["Status"],
                "running": state["Running"],
            }

            # Add optional fields if present
            if "StartedAt" in state:
                status["started_at"] = state["StartedAt"]
            if "ExitCode" in state:
                status["exit_code"] = state["ExitCode"]

            return status

        except NotFound:
            return {
                "state": "not_found",
                "running": False,
            }

    def get_logs(self, runtime_name: str, tail_lines: int) -> str:
        """
        Get recent logs from a trader container.

        Args:
            runtime_name: Container name
            tail_lines: Number of recent lines to retrieve

        Returns:
            Log output as string, empty if container not found
        """
        try:
            container = self.client.containers.get(runtime_name)
            logs_bytes = container.logs(tail=tail_lines)
            return logs_bytes.decode("utf-8")
        except NotFound:
            return ""

    def _ensure_network(self) -> None:
        """
        Ensure the internal network exists, create if needed.

        Creates a bridge network for trader containers to communicate
        securely without exposing ports to the host.
        """
        try:
            self.client.networks.get(self.NETWORK_NAME)
        except NotFound:
            self.client.networks.create(
                self.NETWORK_NAME,
                driver="bridge",
            )
