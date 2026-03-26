"""
Runtime abstraction layer for trader container lifecycle management.

Provides interface for creating, managing, and monitoring trader containers
across different container orchestration platforms.
"""

from hyper_trader_api.runtime.base import TraderRuntime
from hyper_trader_api.runtime.docker_runtime import DockerRuntime
from hyper_trader_api.runtime.factory import get_runtime

__all__ = ["TraderRuntime", "DockerRuntime", "get_runtime"]
