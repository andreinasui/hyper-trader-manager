"""
Base protocol for trader runtime abstraction.

Defines the interface that all runtime implementations must follow
for managing trader services lifecycle using Docker Swarm.
"""

from pathlib import Path
from typing import Any, Protocol


class TraderRuntime(Protocol):
    """
    Protocol for trader service runtime operations.

    Defines the interface for creating and managing trader services
    using Docker Swarm with native secret management.
    """

    def create_trader(
        self,
        trader: Any,  # Trader model instance
        config_path: Path,
        private_key: str,
    ) -> None:
        """
        Create Docker secret and start a new trader service.

        Creates a Docker secret for the private key, then creates a Swarm
        service with the secret attached.

        Args:
            trader: Trader model instance with runtime_name, image_tag, wallet_address
            config_path: Path to config JSON file to mount into service
            private_key: Plain text private key to store as Docker secret

        Raises:
            APIError: If service with same name already exists
            OSError: If config file doesn't exist or isn't readable
        """
        ...

    def restart_trader(self, runtime_name: str) -> None:
        """
        Force update a trader service to trigger restart.

        Args:
            runtime_name: Service name to restart

        Raises:
            NotFound: If service doesn't exist
        """
        ...

    def remove_trader(self, runtime_name: str, trader_id: str) -> None:
        """
        Stop service and remove associated Docker secret.

        Args:
            runtime_name: Service name to remove
            trader_id: Trader ID used in secret naming

        Raises:
            NotFound: If service doesn't exist
        """
        ...

    def get_status(self, runtime_name: str) -> dict[str, Any]:
        """
        Get current status of a trader service.

        Args:
            runtime_name: Service name to check

        Returns:
            Status dictionary with keys:
            - state: Service state (running, complete, not_found, etc.)
            - running: Boolean indicating if service has running tasks
            - replicas: Current/desired replica count

            For missing services, returns: {"state": "not_found", "running": False}
        """
        ...

    def get_logs(self, runtime_name: str, tail_lines: int) -> str:
        """
        Get recent logs from a trader service.

        Args:
            runtime_name: Service name
            tail_lines: Number of recent log lines to retrieve

        Returns:
            Log output as string. Empty string if service doesn't exist.
        """
        ...
