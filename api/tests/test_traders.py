"""
Trader endpoint tests using mocks.
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.database import get_db
from api.services.trader_service import TraderNotFoundError, TraderOwnershipError


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def client(mock_db):
    def override_get_db():
        yield mock_db
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.plan_tier = "free"
    user.is_admin = False
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def mock_trader(mock_user):
    trader = MagicMock()
    trader.id = uuid.uuid4()
    trader.user_id = mock_user.id
    trader.wallet_address = "0x1234567890123456789012345678901234567890"
    trader.k8s_name = "trader-12345678"
    trader.status = "running"
    trader.image_tag = "latest"
    trader.created_at = datetime.now(timezone.utc)
    trader.updated_at = datetime.now(timezone.utc)
    trader.latest_config = MagicMock()
    trader.latest_config.config_json = {"name": "Test", "exchange": "hyperliquid"}
    return trader


class TestCreateTrader:
    """Tests for POST /api/v1/traders/"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_create_trader_success(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.create_trader.return_value = mock_trader
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/traders/",
            headers={"Authorization": "Bearer valid_token"},
            json={
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "private_key": "0x1234567890123456789012345678901234567890123456789012345678901234",
                "config": {"name": "Test Trader", "exchange": "hyperliquid"}
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["wallet_address"] == mock_trader.wallet_address
        assert data["k8s_name"] == mock_trader.k8s_name
        mock_service.create_trader.assert_called_once()

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    def test_create_trader_invalid_wallet_format(self, mock_get_user, client, mock_user):
        mock_get_user.return_value = mock_user

        response = client.post(
            "/api/v1/traders/",
            headers={"Authorization": "Bearer valid_token"},
            json={
                "wallet_address": "invalid_address",
                "private_key": "0x1234567890123456789012345678901234567890123456789012345678901234",
                "config": {"name": "Test"}
            }
        )

        assert response.status_code == 422

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_create_trader_duplicate_wallet(self, mock_service_class, mock_get_user, client, mock_user):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.create_trader.side_effect = ValueError("Trader already exists for wallet")
        mock_service_class.return_value = mock_service

        response = client.post(
            "/api/v1/traders/",
            headers={"Authorization": "Bearer valid_token"},
            json={
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "private_key": "0x1234567890123456789012345678901234567890123456789012345678901234",
                "config": {"name": "Test"}
            }
        )

        assert response.status_code == 409

    def test_create_trader_unauthenticated(self, client):
        """Test creating trader without authentication."""
        response = client.post(
            "/api/v1/traders/",
            json={
                "wallet_address": "0x1234567890123456789012345678901234567890",
                "private_key": "0x1234567890123456789012345678901234567890123456789012345678901234",
                "config": {"name": "Test"}
            }
        )

        assert response.status_code == 401


class TestListTraders:
    """Tests for GET /api/v1/traders"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_list_traders_empty(self, mock_service_class, mock_get_user, client, mock_user):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.list_traders.return_value = []
        mock_service_class.return_value = mock_service

        response = client.get(
            "/api/v1/traders",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["traders"] == []

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_list_traders_with_data(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.list_traders.return_value = [mock_trader]
        mock_service_class.return_value = mock_service

        response = client.get(
            "/api/v1/traders",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["traders"]) == 1
        assert data["traders"][0]["wallet_address"] == mock_trader.wallet_address

    def test_list_traders_unauthenticated(self, client):
        response = client.get("/api/v1/traders")
        assert response.status_code == 401


class TestGetTrader:
    """Tests for GET /api/v1/traders/{id}"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_get_trader_success(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.return_value = mock_trader
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/traders/{mock_trader.id}",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["wallet_address"] == mock_trader.wallet_address

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_get_trader_not_found(self, mock_service_class, mock_get_user, client, mock_user):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.side_effect = TraderNotFoundError("Trader not found")
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/traders/{uuid.uuid4()}",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 404

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_get_trader_forbidden(self, mock_service_class, mock_get_user, client, mock_user):
        """Test accessing another user's trader."""
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.side_effect = TraderOwnershipError("Access denied")
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/traders/{uuid.uuid4()}",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 403


class TestUpdateTrader:
    """Tests for PATCH /api/v1/traders/{id}"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_update_trader_success(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        
        # Update trader's config for the test
        updated_trader = mock_trader
        updated_trader.latest_config.config_json = {"name": "Updated Trader", "exchange": "hyperliquid"}
        
        mock_service = MagicMock()
        mock_service.update_trader.return_value = updated_trader
        mock_service_class.return_value = mock_service

        response = client.patch(
            f"/api/v1/traders/{mock_trader.id}",
            headers={"Authorization": "Bearer valid_token"},
            json={"config": {"name": "Updated Trader", "exchange": "hyperliquid"}}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["latest_config"]["name"] == "Updated Trader"

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_update_trader_not_found(self, mock_service_class, mock_get_user, client, mock_user):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.update_trader.side_effect = TraderNotFoundError("Trader not found")
        mock_service_class.return_value = mock_service

        response = client.patch(
            f"/api/v1/traders/{uuid.uuid4()}",
            headers={"Authorization": "Bearer valid_token"},
            json={"config": {"name": "Updated"}}
        )

        assert response.status_code == 404


class TestDeleteTrader:
    """Tests for DELETE /api/v1/traders/{id}"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_delete_trader_success(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.return_value = mock_trader
        mock_service.delete_trader.return_value = None
        mock_service_class.return_value = mock_service

        response = client.delete(
            f"/api/v1/traders/{mock_trader.id}",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        assert data["wallet_address"] == mock_trader.wallet_address
        mock_service.delete_trader.assert_called_once()

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_delete_trader_not_found(self, mock_service_class, mock_get_user, client, mock_user):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.side_effect = TraderNotFoundError("Trader not found")
        mock_service_class.return_value = mock_service

        response = client.delete(
            f"/api/v1/traders/{uuid.uuid4()}",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 404

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_delete_trader_forbidden(self, mock_service_class, mock_get_user, client, mock_user):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.side_effect = TraderOwnershipError("Access denied")
        mock_service_class.return_value = mock_service

        response = client.delete(
            f"/api/v1/traders/{uuid.uuid4()}",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 403


class TestRestartTrader:
    """Tests for POST /api/v1/traders/{id}/restart"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_restart_trader_success(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.return_value = mock_trader
        mock_service.restart_trader.return_value = None
        mock_service_class.return_value = mock_service

        response = client.post(
            f"/api/v1/traders/{mock_trader.id}/restart",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "restart initiated" in data["message"]
        assert data["k8s_name"] == mock_trader.k8s_name

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_restart_trader_not_found(self, mock_service_class, mock_get_user, client, mock_user):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.side_effect = TraderNotFoundError("Trader not found")
        mock_service_class.return_value = mock_service

        response = client.post(
            f"/api/v1/traders/{uuid.uuid4()}/restart",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 404


class TestGetTraderStatus:
    """Tests for GET /api/v1/traders/{id}/status"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_get_trader_status_success(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader_status.return_value = {
            "id": str(mock_trader.id),
            "wallet_address": mock_trader.wallet_address,
            "k8s_name": mock_trader.k8s_name,
            "status": "running",
            "k8s_status": {
                "exists": True,
                "pod_phase": "Running",
                "ready": True,
                "restarts": 0,
                "pod_ip": "10.0.0.1",
                "node": "node-1",
                "started_at": datetime.now(timezone.utc).isoformat()
            }
        }
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/traders/{mock_trader.id}/status",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["k8s_status"]["pod_phase"] == "Running"
        assert data["k8s_status"]["ready"] is True


class TestGetTraderLogs:
    """Tests for GET /api/v1/traders/{id}/logs"""

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_get_trader_logs_success(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.return_value = mock_trader
        mock_service.get_trader_logs.return_value = "Log line 1\nLog line 2\nLog line 3"
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/traders/{mock_trader.id}/logs",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "Log line 1" in data["logs"]
        assert data["tail_lines"] == 100  # default

    @patch("api.middleware.jwt_auth.get_current_user_from_jwt")
    @patch("api.routers.traders.TraderService")
    def test_get_trader_logs_with_tail(self, mock_service_class, mock_get_user, client, mock_user, mock_trader):
        mock_get_user.return_value = mock_user
        mock_service = MagicMock()
        mock_service.get_trader.return_value = mock_trader
        mock_service.get_trader_logs.return_value = "Recent log"
        mock_service_class.return_value = mock_service

        response = client.get(
            f"/api/v1/traders/{mock_trader.id}/logs?tail_lines=50",
            headers={"Authorization": "Bearer valid_token"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tail_lines"] == 50
        mock_service.get_trader_logs.assert_called_once_with(mock_trader.id, mock_user.id, 50)
