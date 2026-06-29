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
    """Tests for creating trader secrets and services."""

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_create_secret_creates_docker_secret(self, mock_docker):
        """create_secret should create a Docker secret for private key."""
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        # Secret doesn't exist yet — get() raises NotFound
        mock_client.secrets.get.side_effect = NotFound("not found")
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        runtime.create_secret("trader-123", "0xprivatekey")

        # Verify secret was created
        mock_client.secrets.create.assert_called_once()
        call_kwargs = mock_client.secrets.create.call_args.kwargs
        assert call_kwargs["name"] == "ht_trader-123_private_key"
        assert call_kwargs["data"] == b"0xprivatekey"
        assert call_kwargs["labels"]["trader_id"] == "trader-123"

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_create_service_creates_service_with_secret_and_config(self, mock_docker):
        """create_service should create a service with secret and config attached."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_secret = MagicMock()
        mock_secret.id = "secret-123"
        mock_client.secrets.get.return_value = mock_secret
        mock_config = MagicMock()
        mock_config.id = "config-123"
        mock_client.configs.create.return_value = mock_config
        mock_client.configs.get.return_value = mock_config
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        config_data = '{"provider_settings": {"copy_account": {"address": "0x5678"}}}'

        trader = MagicMock()
        trader.id = "trader-123"
        trader.runtime_name = "trader-abc"
        trader.image_tag = "v1.0"
        trader.wallet_address = "0x1234"

        runtime.create_service(trader, config_data)

        # Verify service was created
        mock_client.services.create.assert_called_once()
        call_kwargs = mock_client.services.create.call_args.kwargs
        assert call_kwargs["name"] == "trader-abc"
        assert call_kwargs["image"] == "ghcr.io/andreinasui/hyper-trader:v1.0"
        assert len(call_kwargs["secrets"]) == 1
        assert len(call_kwargs["configs"]) == 1


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
        runtime.remove_service("trader-abc", True, "trader-123")

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
        runtime.remove_service("trader-abc", True, "trader-123")

        mock_service.remove.assert_called_once()


class TestDockerRuntimeListLocalImageTags:
    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_returns_semver_tags_sorted_desc(self, mock_docker):
        """Should return semver tags sorted newest first."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}

        mock_image1 = MagicMock()
        mock_image1.tags = ["ghcr.io/andreinasui/hyper-trader:0.4.3"]
        mock_image2 = MagicMock()
        mock_image2.tags = ["ghcr.io/andreinasui/hyper-trader:0.4.4"]
        mock_image3 = MagicMock()
        mock_image3.tags = ["ghcr.io/andreinasui/hyper-trader:0.3.0"]
        mock_client.images.list.return_value = [mock_image1, mock_image2, mock_image3]
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        tags = runtime.list_local_image_tags()

        assert tags == ["0.4.4", "0.4.3", "0.3.0"]
        mock_client.images.list.assert_called_once_with(name="ghcr.io/andreinasui/hyper-trader")

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_excludes_non_semver_tags(self, mock_docker):
        """Should ignore tags that don't match semver pattern."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}

        mock_image = MagicMock()
        mock_image.tags = [
            "ghcr.io/andreinasui/hyper-trader:0.4.4",
            "ghcr.io/andreinasui/hyper-trader:latest",
            "ghcr.io/andreinasui/hyper-trader:dev",
        ]
        mock_client.images.list.return_value = [mock_image]
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        tags = runtime.list_local_image_tags()

        assert tags == ["0.4.4"]

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_returns_empty_list_when_no_images(self, mock_docker):
        """Should return empty list when no local images found."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_client.images.list.return_value = []
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        tags = runtime.list_local_image_tags()

        assert tags == []

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_returns_empty_on_exception(self, mock_docker):
        """Should return empty list if Docker API raises an exception."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_client.images.list.side_effect = Exception("Docker error")
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        tags = runtime.list_local_image_tags()

        assert tags == []


class TestDockerRuntimePullImage:
    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_pull_image_calls_docker_pull(self, mock_docker):
        """pull_image should call docker images.pull with correct args."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        runtime.pull_image("0.4.4")

        mock_client.images.pull.assert_called_once_with(
            "ghcr.io/andreinasui/hyper-trader", tag="0.4.4"
        )


class TestDockerRuntimeUpdateServiceImage:
    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_updates_service_image(self, mock_docker):
        """update_service_image should call service.update with new image."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        runtime.update_service_image("trader-abc123", "0.4.4")

        mock_client.services.get.assert_called_once_with("trader-abc123")
        mock_service.update.assert_called_once_with(
            image="ghcr.io/andreinasui/hyper-trader:0.4.4",
            update_config={"Parallelism": 0, "FailureAction": "continue", "Order": "stop-first"},
        )

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_raises_not_found_for_missing_service(self, mock_docker):
        """update_service_image should raise NotFound if service doesn't exist."""
        from docker.errors import NotFound

        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_client.services.get.side_effect = NotFound("service not found")
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        import pytest

        with pytest.raises(NotFound):
            runtime.update_service_image("trader-missing", "0.4.4")


class TestDockerRuntimeLogConfig:
    """Tests that trader services are created with log driver config."""

    @patch("hyper_trader_api.runtime.docker_runtime.docker")
    def test_create_service_sets_log_driver(self, mock_docker):
        """create_service should pass json-file log driver options to services.create."""
        from unittest.mock import MagicMock

        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        mock_client.secrets.get.return_value = MagicMock(id="secret-id")
        mock_client.networks.get.return_value = MagicMock()
        mock_client.configs.get.return_value = MagicMock(id="config-id")
        # create_config calls configs.list then configs.create
        mock_client.configs.list.return_value = []
        mock_docker.from_env.return_value = mock_client

        from hyper_trader_api.runtime.docker_runtime import DockerRuntime

        runtime = DockerRuntime(mock_client)

        trader = MagicMock()
        trader.id = "test-trader-id"
        trader.runtime_name = "trader-ab12cd34"
        trader.image_tag = "0.4.4"
        trader.wallet_address = "0xab12cd34ef56gh78"

        runtime.create_service(trader, "{}")

        call_kwargs = mock_client.services.create.call_args.kwargs
        assert call_kwargs.get("log_driver") == "json-file"
        assert call_kwargs.get("log_driver_options") == {"max-size": "100m", "max-file": "7"}


class TestDockerRuntimeGetLogsTimeRange:
    """Tests for get_logs with time range filtering."""

    def _make_runtime(self):
        """Create a DockerRuntime with a mocked Docker client."""
        mock_client = MagicMock()
        mock_client.swarm.attrs = {"ID": "swarm-id"}
        from hyper_trader_api.runtime.docker_runtime import DockerRuntime
        return DockerRuntime(mock_client), mock_client

    def test_get_logs_uses_tail_when_no_since(self):
        """Without since, get_logs uses tail=tail_lines and no timestamps."""
        runtime, mock_client = self._make_runtime()
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        mock_service.logs.return_value = iter([b"line1\nline2\n"])

        runtime.get_logs("trader-abc", tail_lines=50)

        mock_service.logs.assert_called_once_with(stdout=True, stderr=True, tail=50)

    def test_get_logs_uses_since_and_timestamps_when_since_given(self):
        """With since, get_logs uses since=dt, timestamps=True, tail=1000."""
        from datetime import datetime, timezone
        runtime, mock_client = self._make_runtime()
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        mock_service.logs.return_value = iter([b""])

        since = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        runtime.get_logs("trader-abc", since=since)

        mock_service.logs.assert_called_once_with(
            stdout=True, stderr=True, since=since, timestamps=True, tail=1000
        )

    def test_get_logs_uses_tail_all_when_all_lines_true(self):
        """With all_lines=True, get_logs uses tail='all'."""
        from datetime import datetime, timezone
        runtime, mock_client = self._make_runtime()
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service
        mock_service.logs.return_value = iter([b""])

        since = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        runtime.get_logs("trader-abc", since=since, all_lines=True)

        mock_service.logs.assert_called_once_with(
            stdout=True, stderr=True, since=since, timestamps=True, tail="all"
        )

    def test_get_logs_filters_lines_beyond_until(self):
        """Lines with timestamps after 'until' are excluded from the result."""
        from datetime import datetime, timezone
        runtime, mock_client = self._make_runtime()
        mock_service = MagicMock()
        mock_client.services.get.return_value = mock_service

        # Two lines: one within range, one after 'until'
        log_bytes = (
            b"2026-05-03T10:00:00.000000000Z within range\n"
            b"2026-05-03T12:00:00.000000000Z after until\n"
        )
        mock_service.logs.return_value = iter([log_bytes])

        since = datetime(2026, 5, 3, 9, 0, 0, tzinfo=timezone.utc)
        until = datetime(2026, 5, 3, 11, 0, 0, tzinfo=timezone.utc)

        result = runtime.get_logs("trader-abc", since=since, until=until)

        assert "within range" in result
        assert "after until" not in result
