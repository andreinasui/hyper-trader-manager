"""
Factory for creating trader runtime instances.

Provides a simple factory function to get the appropriate runtime
implementation based on configuration.
"""

import docker
from hyper_trader_api.runtime.base import TraderRuntime
from hyper_trader_api.runtime.docker_runtime import DockerRuntime


def get_runtime() -> TraderRuntime:
    """
    Get a trader runtime instance.

    Currently returns DockerRuntime using the default Docker environment.
    Future versions may support additional runtime types.

    Returns:
        TraderRuntime instance for managing trader containers
    """
    client = docker.from_env()
    return DockerRuntime(client)
