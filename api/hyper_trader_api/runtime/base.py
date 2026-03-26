"""
Base protocol for trader runtime abstraction.

Defines the interface that all runtime implementations must follow
for managing trader container lifecycle.
"""

from pathlib import Path
from typing import Any, Protocol


class TraderRuntime(Protocol):
    """
    Protocol for trader container runtime operations.

    Defines the interface for creating and managing trader containers
    across different orchestration platforms (Docker, Kubernetes, etc.).
    """

    def create_trader(
        self,
        trader: Any,  # Trader model instance
        config_path: Path,
        secret_env: dict[str, str],
    ) -> None:
        """
        Create and start a new trader container.

        Args:
            trader: Trader model instance with runtime_name, image_tag, wallet_address
            config_path: Path to config JSON file to mount into container
            secret_env: Dictionary of environment variables (keys=var names, values=secrets)

        Raises:
            APIError: If container with same name already exists
            OSError: If config file doesn't exist or isn't readable
        """
        ...

    def restart_trader(self, runtime_name: str) -> None:
        """
        Restart an existing trader container.

        Args:
            runtime_name: Container name to restart

        Raises:
            NotFound: If container doesn't exist
        """
        ...

    def remove_trader(self, runtime_name: str) -> None:
        """
        Stop and remove a trader container.

        Args:
            runtime_name: Container name to remove

        Raises:
            NotFound: If container doesn't exist
        """
        ...

    def get_status(self, runtime_name: str) -> dict[str, Any]:
        """
        Get current status of a trader container.

        Args:
            runtime_name: Container name to check

        Returns:
            Status dictionary with keys:
            - state: Container state (running, exited, not_found, etc.)
            - running: Boolean indicating if container is running
            - started_at: ISO timestamp when container started (if running)
            - exit_code: Exit code (if exited)

            For missing containers, returns: {"state": "not_found", "running": False}
        """
        ...

    def get_logs(self, runtime_name: str, tail_lines: int) -> str:
        """
        Get recent logs from a trader container.

        Args:
            runtime_name: Container name
            tail_lines: Number of recent log lines to retrieve

        Returns:
            Log output as string. Empty string if container doesn't exist.
        """
        ...
