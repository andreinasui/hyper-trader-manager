"""
Tests for Docker Swarm runtime implementation.

Tests the DockerRuntime class with mocked Docker client.
"""

from unittest.mock import MagicMock, patch

from docker.errors import APIError, NotFound


class TestDockerRuntimeSwarmInit:
    """Tests for Swarm initialization."""

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_initializes_swarm_if_not_active(self, mock_docker):
        """Runtime should initialize swarm if not already active."""
        mock_client = MagicMock()
        # Simulate not in swarm mode
        mock_client.swarm.attrs.__getitem__.side_effect = APIError("not in swarm")
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        DockerRuntime(mock_client)

        mock_client.swarm.init.assert_called_once()

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_skips_swarm_init_if_already_active(self, mock_docker):
        """Runtime should not reinitialize if already in swarm mode."""
        mock_client = MagicMock()
        # Simulate already in swarm mode
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        DockerRuntime(mock_client)

        mock_client.swarm.init.assert_not_called()


class TestDockerRuntimeCreateTrader:
    """Tests for creating trader services."""

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_create_trader_creates_secret(self, mock_docker, tmp_path):
        """create_trader should create a Docker secret for private key."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_secret = MagicMock()
        mock_secret.id = "secret-123"
        mock_client.secrets.create.return_value = mock_secret
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        # Create config file
        config_path = tmp_path / "config.json"
        config_path.write_text("{}")

        # Mock trader
        trader = MagicMock()
        trader.id = "trader-123"
        trader.runtime_name = "trader-abc"
        trader.image_tag = "latest"
        trader.wallet_address = "0x1234"

        runtime.create_trader(trader, config_path, "0xprivatekey")

        # Verify secret was created
        mock_client.secrets.create.assert_called_once()
        call_kwargs = mock_client.secrets.create.call_args.kwargs
        assert call_kwargs["name"] == "ht_trader-123_private_key"
        assert call_kwargs["data"] == b"0xprivatekey"
        assert call_kwargs["labels"]["trader_id"] == "trader-123"

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_create_trader_creates_service_with_secret(self, mock_docker, tmp_path):
        """create_trader should create a service with secret attached."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_secret = MagicMock()
        mock_secret.id = "secret-123"
        mock_client.secrets.create.return_value = mock_secret
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        config_path = tmp_path / "config.json"
        config_path.write_text("{}")

        trader = MagicMock()
        trader.id = "trader-123"
        trader.runtime_name = "trader-abc"
        trader.image_tag = "v1.0"
        trader.wallet_address = "0x1234"

        runtime.create_trader(trader, config_path, "0xprivatekey")

        # Verify service was created
        mock_client.services.create.assert_called_once()
        call_kwargs = mock_client.services.create.call_args.kwargs
        assert call_kwargs["name"] == "trader-abc"
        assert call_kwargs["image"] == "hyper-trader:v1.0"
        assert len(call_kwargs["secrets"]) == 1


class TestDockerRuntimeRemoveTrader:
    """Tests for removing trader services."""

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_remove_trader_removes_service_and_secret(self, mock_docker):
        """remove_trader should remove both service and secret."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        mock_secret = MagicMock()
        mock_client.secrets.get.return_value = mock_secret
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)
        runtime.remove_trader("trader-abc", "trader-123")

        mock_service.remove.assert_called_once()
        mock_secret.remove.assert_called_once()

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_remove_trader_handles_missing_secret(self, mock_docker):
        """remove_trader should not fail if secret already removed."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        mock_client.secrets.get.side_effect = NotFound("not found")
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        # Should not raise
        runtime.remove_trader("trader-abc", "trader-123")

        mock_service.remove.assert_called_once()
