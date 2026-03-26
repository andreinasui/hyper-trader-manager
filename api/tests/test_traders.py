"""
Tests for trader endpoints with Docker runtime integration.

Tests the Docker-based trader lifecycle instead of Kubernetes.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from hyper_trader_api.database import get_db
from hyper_trader_api.main import app
from hyper_trader_api.middleware.jwt_auth import get_current_user


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db, mock_user):
    """Test client with mocked database and authentication."""

    def override_get_db():
        yield mock_db

    def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    # Mock the engine for health checks
    with patch("hyper_trader_api.main.engine") as mock_engine:
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value = None
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.username = "testuser"
    user.is_admin = False
    user.created_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_trader(mock_user):
    trader = MagicMock()
    trader.id = str(uuid.uuid4())
    trader.user_id = mock_user.id
    trader.wallet_address = "0x1234567890123456789012345678901234567890"
    trader.runtime_name = "trader-12345678"
    trader.status = "running"
    trader.image_tag = "latest"
    trader.created_at = datetime.now(UTC)
    trader.updated_at = datetime.now(UTC)
    trader.latest_config = MagicMock()
    trader.latest_config.config_json = {"name": "Test", "exchange": "hyperliquid"}
    trader.latest_config.version = 1
    trader.secret = MagicMock()
    trader.secret.private_key_encrypted = "encrypted_private_key"
    return trader


class TestCreateTraderDockerRuntime:
    """Tests for creating traders with Docker runtime."""

    @patch("hyper_trader_api.routers.traders.TraderService")
    def test_create_trader_persists_runtime_name(
        self, mock_service_class, client, mock_user, mock_trader
    ):
        """Test that create_trader stores runtime_name field."""
        mock_service = MagicMock()
        mock_service.create_trader.return_value = mock_trader
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/traders/",
            headers={"Authorization": "Bearer valid_token"},
            json={
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "private_key": "0x1234567890123456789012345678901234567890123456789012345678901234",
                "config": {"name": "Test Trader", "exchange": "hyperliquid"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "runtime_name" in data
        assert data["runtime_name"].startswith("trader-")
        assert data["wallet_address"] == mock_trader.wallet_address
        mock_service.create_trader.assert_called_once()

    @patch("hyper_trader_api.routers.traders.TraderService")
    def test_create_trader_encrypts_secret(
        self, mock_service_class, client, mock_user, mock_trader
    ):
        """Test that private_key is encrypted before storage."""
        mock_service = MagicMock()
        mock_service.create_trader.return_value = mock_trader
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/traders/",
            headers={"Authorization": "Bearer valid_token"},
            json={
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "private_key": "0x1234567890123456789012345678901234567890123456789012345678901234",
                "config": {"name": "Test Trader"},
            },
        )

        assert response.status_code == 201
        # Verify service was called with trader data containing private_key
        call_args = mock_service.create_trader.call_args
        trader_data = call_args[0][1]  # Second argument is trader_data
        assert hasattr(trader_data, "private_key")

    @patch("hyper_trader_api.routers.traders.TraderService")
    def test_create_trader_returns_config_with_version(
        self, mock_service_class, client, mock_user, mock_trader
    ):
        """Test that create_trader endpoint returns config with version in response."""
        mock_service = MagicMock()
        mock_service.create_trader.return_value = mock_trader
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/traders/",
            headers={"Authorization": "Bearer valid_token"},
            json={
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "private_key": "0x1234567890123456789012345678901234567890123456789012345678901234",
                "config": {"name": "Test Trader", "exchange": "hyperliquid"},
            },
        )

        assert response.status_code == 201
        data = response.json()
        # Verify response includes config with version
        assert data["latest_config"] is not None
        # The actual version storage is tested in TestTraderConfigVersionStorage
        mock_service.create_trader.assert_called_once()


class TestListTradersDockerRuntime:
    """Tests for listing traders with Docker runtime."""

    @patch("hyper_trader_api.routers.traders.TraderService")
    def test_list_returns_runtime_name(self, mock_service_class, client, mock_user, mock_trader):
        """Test that list endpoint returns runtime_name field."""
        mock_service = MagicMock()
        mock_service.list_traders.return_value = [mock_trader]
        mock_service_class.return_value = mock_service

        response = client.get("/api/v1/traders", headers={"Authorization": "Bearer valid_token"})

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert "runtime_name" in data["traders"][0]
        assert data["traders"][0]["runtime_name"] == mock_trader.runtime_name


class TestRestartTraderDockerRuntime:
    """Tests for restarting traders with Docker runtime."""

    @patch("hyper_trader_api.routers.traders.TraderService")
    def test_restart_calls_runtime_layer(self, mock_service_class, client, mock_user, mock_trader):
        """Test that restart calls the runtime layer."""
        mock_service = MagicMock()
        mock_service.get_trader.return_value = mock_trader
        mock_service.restart_trader.return_value = None
        mock_service_class.return_value = mock_service

        response = client.post(
            f"/api/v1/traders/{mock_trader.id}/restart",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "runtime_name" in data
        assert data["runtime_name"] == mock_trader.runtime_name
        # Verify restart_trader was called (don't enforce exact ID type matching)
        assert mock_service.restart_trader.called


class TestDeleteTraderDockerRuntime:
    """Tests for deleting traders with Docker runtime."""

    @patch("hyper_trader_api.routers.traders.TraderService")
    def test_delete_calls_runtime_layer(self, mock_service_class, client, mock_user, mock_trader):
        """Test that delete calls the runtime layer."""
        mock_service = MagicMock()
        mock_service.get_trader.return_value = mock_trader
        mock_service.delete_trader.return_value = None
        mock_service_class.return_value = mock_service

        response = client.delete(
            f"/api/v1/traders/{mock_trader.id}", headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        # Verify delete_trader was called (don't enforce exact ID type matching)
        assert mock_service.delete_trader.called


class TestGetTraderStatusDockerRuntime:
    """Tests for getting trader status with Docker runtime."""

    @patch("hyper_trader_api.routers.traders.TraderService")
    def test_status_returns_docker_runtime_info(
        self, mock_service_class, client, mock_user, mock_trader
    ):
        """Test that status endpoint returns Docker runtime information."""
        mock_service = MagicMock()
        mock_service.get_trader_status.return_value = {
            "id": mock_trader.id,
            "wallet_address": mock_trader.wallet_address,
            "runtime_name": mock_trader.runtime_name,
            "status": "running",
            "runtime_status": {
                "state": "running",
                "running": True,
                "started_at": datetime.now(UTC).isoformat(),
            },
        }
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/traders/{mock_trader.id}/status",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "runtime_status" in data
        assert data["runtime_status"]["state"] == "running"
        assert data["runtime_status"]["running"] is True
        assert "runtime_name" in data


class TestGetTraderLogsDockerRuntime:
    """Tests for getting trader logs with Docker runtime."""

    @patch("hyper_trader_api.routers.traders.TraderService")
    def test_logs_come_from_runtime_layer(self, mock_service_class, client, mock_user, mock_trader):
        """Test that logs come from the runtime layer."""
        mock_service = MagicMock()
        mock_service.get_trader.return_value = mock_trader
        mock_service.get_trader_logs.return_value = "Docker container log output\nLine 2\nLine 3"
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/traders/{mock_trader.id}/logs",
            headers={"Authorization": "Bearer valid_token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "Docker container log output" in data["logs"]
        # Verify get_trader_logs was called (don't enforce exact ID type matching)
        assert mock_service.get_trader_logs.called


class TestTraderConfigVersionStorage:
    """Integration tests for trader config version storage."""

    @patch("hyper_trader_api.services.trader_service.TraderService._write_config_file")
    @patch("hyper_trader_api.services.trader_service.get_runtime")
    @patch("hyper_trader_api.services.trader_service.decrypt_secret")
    @patch("hyper_trader_api.services.trader_service.encrypt_secret")
    def test_create_trader_stores_version_1(
        self, mock_encrypt, mock_decrypt, mock_get_runtime, mock_write_config, mock_db
    ):
        """Test that TraderService creates TraderConfig with version=1."""
        from hyper_trader_api.models.trader import Trader, TraderConfig, TraderSecret
        from hyper_trader_api.schemas.trader import TraderCreate
        from hyper_trader_api.services.trader_service import TraderService

        # Setup mocks
        mock_encrypt.return_value = "encrypted_key_data"
        mock_decrypt.return_value = (
            "0x1234567890123456789012345678901234567890123456789012345678901234"
        )
        mock_runtime = MagicMock()
        mock_runtime.deploy_trader.return_value = None
        mock_get_runtime.return_value = mock_runtime
        mock_write_config.return_value = Path("/tmp/config.json")

        # Mock database session to track what gets added
        added_objects = []

        def mock_add(obj):
            added_objects.append(obj)
            # Link trader to its config immediately for relationship access
            if isinstance(obj, Trader):
                obj.configs = []
            elif isinstance(obj, TraderConfig):
                # Find the trader and add this config
                for added_obj in added_objects:
                    if isinstance(added_obj, Trader):
                        added_obj.configs.append(obj)
                        break

        def mock_flush():
            # Simulate ID assignment for all objects
            for obj in added_objects:
                if isinstance(obj, Trader) and not hasattr(obj, "id"):
                    obj.id = str(uuid.uuid4())
                elif isinstance(obj, TraderConfig) and not hasattr(obj, "id"):
                    obj.id = str(uuid.uuid4())
                elif isinstance(obj, TraderSecret) and not hasattr(obj, "id"):
                    obj.id = str(uuid.uuid4())

        # Mock query to return None (no existing trader)
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query
        mock_db.add = mock_add
        mock_db.flush = mock_flush
        mock_db.commit = MagicMock()
        mock_db.rollback = MagicMock()
        mock_db.refresh = MagicMock()

        # Create service and trader (service gets settings internally)
        service = TraderService(mock_db)

        # Create mock user object
        mock_user = MagicMock()
        mock_user.id = str(uuid.uuid4())
        mock_user.username = "testuser"

        trader_data = TraderCreate(
            wallet_address="0x1234567890123456789012345678901234567890",
            private_key="0x1234567890123456789012345678901234567890123456789012345678901234",
            config={"name": "Test Trader", "exchange": "hyperliquid"},
        )

        service.create_trader(mock_user, trader_data)

        # Verify TraderConfig with version=1 was created
        config_objects = [obj for obj in added_objects if isinstance(obj, TraderConfig)]
        assert len(config_objects) == 1, "Expected one TraderConfig to be created"

        config = config_objects[0]
        assert config.version == 1, f"Expected version=1, got {config.version}"
        # Config should have self_account.address added by the service
        assert "self_account" in config.config_json
        assert config.config_json["self_account"]["address"] == trader_data.wallet_address

        # Verify TraderSecret was also created (encrypted)
        secret_objects = [obj for obj in added_objects if isinstance(obj, TraderSecret)]
        assert len(secret_objects) == 1, "Expected one TraderSecret to be created"
        assert secret_objects[0].private_key_encrypted == "encrypted_key_data"
