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

    def create_secret(self, trader_id: str, private_key: str) -> str:
        """Create Docker secret for trader private key."""
        ...

    def create_service(self, trader: Any, config_path: Path) -> None:
        """Create Docker Swarm service for trader."""
        ...

    def remove_service(
        self, runtime_name: str, remove_secret: bool = False, trader_id: str = ""
    ) -> None:
        """Remove Docker Swarm trader service"""
        ...

    def service_exists(self, runtime_name: str) -> bool:
        """Check if service exists."""
        ...

    def list_local_image_tags(self) -> list[str]:
        """
        List locally available image tags for the trader image, sorted descending by semver.
        Returns list of tag strings, newest first. Empty list if none found.
        """
        ...

    def pull_image(self, tag: str) -> None:
        """Pull a specific image tag from the registry."""
        ...

    def update_service_image(self, runtime_name: str, new_tag: str) -> None:
        """Update a running Swarm service to use a new image tag."""
        ...
