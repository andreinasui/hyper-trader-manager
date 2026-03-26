"""
Tests for Docker runtime abstraction layer.

Covers:
- Container creation with proper network, restart policy, and mounts
- Container lifecycle operations (restart, remove, status, logs)
- Secret environment variable injection
- Config file mounting behavior
- Error handling for missing containers
"""

from unittest.mock import MagicMock, patch

import pytest

from hyper_trader_api.models.trader import Trader
from hyper_trader_api.runtime.docker_runtime import DockerRuntime


@pytest.fixture
def mock_docker_client():
    """Mock Docker client."""
    client = MagicMock()
    client.networks = MagicMock()
    client.containers = MagicMock()
    return client


@pytest.fixture
def mock_trader():
    """Mock trader instance."""
    trader = MagicMock(spec=Trader)
    trader.runtime_name = "trader-abc123"
    trader.image_tag = "v1.2.3"
    trader.wallet_address = "0x1234567890abcdef"
    return trader


@pytest.fixture
def config_path(tmp_path):
    """Create a temporary config file."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"exchange": "hyperliquid"}')
    return config_file


@pytest.fixture
def secret_env():
    """Sample secret environment variables."""
    return {
        "TRADER_PRIVATE_KEY": "0xsecret123",
        "API_KEY": "test-api-key",
    }


class TestDockerRuntimeCreation:
    """Tests for container creation."""

    def test_create_trader_uses_internal_network(
        self, mock_docker_client, mock_trader, config_path, secret_env
    ):
        """Test that trader containers are created on internal network."""
        runtime = DockerRuntime(mock_docker_client)
        runtime.create_trader(mock_trader, config_path, secret_env)

        # Verify container was created with correct network
        mock_docker_client.containers.run.assert_called_once()
        call_kwargs = mock_docker_client.containers.run.call_args[1]
        assert call_kwargs["network"] == "hyper-trader-internal"

    def test_create_trader_uses_unless_stopped_restart_policy(
        self, mock_docker_client, mock_trader, config_path, secret_env
    ):
        """Test that containers use unless-stopped restart policy."""
        runtime = DockerRuntime(mock_docker_client)
        runtime.create_trader(mock_trader, config_path, secret_env)

        call_kwargs = mock_docker_client.containers.run.call_args[1]
        assert call_kwargs["restart_policy"] == {"Name": "unless-stopped"}

    def test_create_trader_mounts_config_readonly(
        self, mock_docker_client, mock_trader, config_path, secret_env
    ):
        """Test that config file is mounted read-only to /app/config.json."""
        runtime = DockerRuntime(mock_docker_client)
        runtime.create_trader(mock_trader, config_path, secret_env)

        call_kwargs = mock_docker_client.containers.run.call_args[1]
        volumes = call_kwargs["volumes"]

        # Check that config is mounted
        assert str(config_path) in volumes
        mount_config = volumes[str(config_path)]
        assert mount_config["bind"] == "/app/config.json"
        assert mount_config["mode"] == "ro"

    def test_create_trader_sets_environment_variables(
        self, mock_docker_client, mock_trader, config_path, secret_env
    ):
        """Test that secret environment variables are passed to container."""
        runtime = DockerRuntime(mock_docker_client)
        runtime.create_trader(mock_trader, config_path, secret_env)

        call_kwargs = mock_docker_client.containers.run.call_args[1]
        environment = call_kwargs["environment"]

        assert environment["TRADER_PRIVATE_KEY"] == "0xsecret123"
        assert environment["API_KEY"] == "test-api-key"

    def test_create_trader_uses_correct_image_and_name(
        self, mock_docker_client, mock_trader, config_path, secret_env
    ):
        """Test that correct image tag and container name are used."""
        runtime = DockerRuntime(mock_docker_client)
        runtime.create_trader(mock_trader, config_path, secret_env)

        # Check image
        call_args = mock_docker_client.containers.run.call_args[0]
        assert "hyper-trader:v1.2.3" in call_args[0]

        # Check container name
        call_kwargs = mock_docker_client.containers.run.call_args[1]
        assert call_kwargs["name"] == "trader-abc123"

    def test_create_trader_runs_in_detached_mode(
        self, mock_docker_client, mock_trader, config_path, secret_env
    ):
        """Test that container runs in detached mode."""
        runtime = DockerRuntime(mock_docker_client)
        runtime.create_trader(mock_trader, config_path, secret_env)

        call_kwargs = mock_docker_client.containers.run.call_args[1]
        assert call_kwargs["detach"] is True

    def test_create_trader_creates_network_if_not_exists(
        self, mock_docker_client, mock_trader, config_path, secret_env
    ):
        """Test that internal network is created if it doesn't exist."""
        # Simulate network not found
        from docker.errors import NotFound

        mock_docker_client.networks.get.side_effect = NotFound("network not found")

        runtime = DockerRuntime(mock_docker_client)
        runtime.create_trader(mock_trader, config_path, secret_env)

        # Verify network creation was attempted
        mock_docker_client.networks.create.assert_called_once_with(
            "hyper-trader-internal",
            driver="bridge",
        )

    def test_create_trader_raises_if_config_missing(
        self, mock_docker_client, mock_trader, secret_env, tmp_path
    ):
        """Test that creation fails if config file doesn't exist."""
        nonexistent_config = tmp_path / "missing.json"

        runtime = DockerRuntime(mock_docker_client)

        with pytest.raises(OSError, match="Config file not found"):
            runtime.create_trader(mock_trader, nonexistent_config, secret_env)

    def test_create_trader_raises_if_container_exists(
        self, mock_docker_client, mock_trader, config_path, secret_env
    ):
        """Test that creation fails if container already exists."""
        from docker.errors import APIError

        mock_docker_client.containers.run.side_effect = APIError("Conflict")

        runtime = DockerRuntime(mock_docker_client)

        with pytest.raises(APIError):
            runtime.create_trader(mock_trader, config_path, secret_env)


class TestDockerRuntimeLifecycle:
    """Tests for container lifecycle operations."""

    def test_restart_trader_restarts_container(self, mock_docker_client):
        """Test that restart operation works."""
        mock_container = MagicMock()
        mock_docker_client.containers.get.return_value = mock_container

        runtime = DockerRuntime(mock_docker_client)
        runtime.restart_trader("trader-abc123")

        mock_docker_client.containers.get.assert_called_once_with("trader-abc123")
        mock_container.restart.assert_called_once()

    def test_restart_trader_raises_if_not_found(self, mock_docker_client):
        """Test that restart fails if container doesn't exist."""
        from docker.errors import NotFound

        mock_docker_client.containers.get.side_effect = NotFound("not found")

        runtime = DockerRuntime(mock_docker_client)

        with pytest.raises(NotFound):
            runtime.restart_trader("nonexistent")

    def test_remove_trader_stops_and_removes_container(self, mock_docker_client):
        """Test that remove operation stops and removes container."""
        mock_container = MagicMock()
        mock_docker_client.containers.get.return_value = mock_container

        runtime = DockerRuntime(mock_docker_client)
        runtime.remove_trader("trader-abc123")

        mock_docker_client.containers.get.assert_called_once_with("trader-abc123")
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()

    def test_remove_trader_raises_if_not_found(self, mock_docker_client):
        """Test that remove fails if container doesn't exist."""
        from docker.errors import NotFound

        mock_docker_client.containers.get.side_effect = NotFound("not found")

        runtime = DockerRuntime(mock_docker_client)

        with pytest.raises(NotFound):
            runtime.remove_trader("nonexistent")


class TestDockerRuntimeStatus:
    """Tests for container status retrieval."""

    def test_get_status_returns_running_container_info(self, mock_docker_client):
        """Test status retrieval for running container."""
        mock_container = MagicMock()
        mock_container.status = "running"
        mock_container.attrs = {
            "State": {
                "Status": "running",
                "Running": True,
                "StartedAt": "2026-03-26T10:00:00Z",
            }
        }
        mock_docker_client.containers.get.return_value = mock_container

        runtime = DockerRuntime(mock_docker_client)
        status = runtime.get_status("trader-abc123")

        assert status["state"] == "running"
        assert status["running"] is True
        assert "started_at" in status

    def test_get_status_returns_stopped_container_info(self, mock_docker_client):
        """Test status retrieval for stopped container."""
        mock_container = MagicMock()
        mock_container.status = "exited"
        mock_container.attrs = {
            "State": {
                "Status": "exited",
                "Running": False,
                "ExitCode": 1,
            }
        }
        mock_docker_client.containers.get.return_value = mock_container

        runtime = DockerRuntime(mock_docker_client)
        status = runtime.get_status("trader-abc123")

        assert status["state"] == "exited"
        assert status["running"] is False
        assert status["exit_code"] == 1

    def test_get_status_returns_not_found_for_missing_container(self, mock_docker_client):
        """Test that status returns not_found state for missing container."""
        from docker.errors import NotFound

        mock_docker_client.containers.get.side_effect = NotFound("not found")

        runtime = DockerRuntime(mock_docker_client)
        status = runtime.get_status("nonexistent")

        assert status["state"] == "not_found"
        assert status["running"] is False

    def test_get_logs_returns_container_logs(self, mock_docker_client):
        """Test log retrieval from container."""
        mock_container = MagicMock()
        mock_container.logs.return_value = b"Log line 1\nLog line 2\nLog line 3\n"
        mock_docker_client.containers.get.return_value = mock_container

        runtime = DockerRuntime(mock_docker_client)
        logs = runtime.get_logs("trader-abc123", tail_lines=10)

        mock_container.logs.assert_called_once_with(tail=10)
        assert logs == "Log line 1\nLog line 2\nLog line 3\n"

    def test_get_logs_returns_empty_for_missing_container(self, mock_docker_client):
        """Test that logs returns empty string for missing container."""
        from docker.errors import NotFound

        mock_docker_client.containers.get.side_effect = NotFound("not found")

        runtime = DockerRuntime(mock_docker_client)
        logs = runtime.get_logs("nonexistent", tail_lines=10)

        assert logs == ""


class TestDockerRuntimeFactory:
    """Tests for runtime factory."""

    @patch("hyper_trader_api.runtime.factory.docker.from_env")
    def test_get_runtime_returns_docker_runtime(self, mock_from_env):
        """Test that factory returns DockerRuntime instance."""
        from hyper_trader_api.runtime.factory import get_runtime

        mock_client = MagicMock()
        mock_from_env.return_value = mock_client

        runtime = get_runtime()

        assert isinstance(runtime, DockerRuntime)
        mock_from_env.assert_called_once()
