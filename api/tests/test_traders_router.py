"""
Tests for traders router endpoints.

Tests for trader CRUD and management operations:
- POST /api/v1/traders/
- POST /api/v1/traders/{id}/start
- POST /api/v1/traders/{id}/stop
- PATCH /api/v1/traders/{id}
- PATCH /api/v1/traders/{id}/config
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from hyper_trader_api.services.trader_service import (
    TraderNotFoundError,
    TraderOwnershipError,
    TraderServiceError,
)


@pytest.fixture
def auth_client(client, mock_user):
    """Test client with authentication override."""
    from hyper_trader_api.main import app
    from hyper_trader_api.middleware.session_auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_config():
    """Sample trader configuration."""
    return {
        "provider_settings": {
            "exchange": "hyperliquid",
            "network": "mainnet",
            "self_account": {
                "address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
            },
            "copy_account": {
                "address": "0x1234567890abcdef1234567890abcdef12345678",
            },
        },
        "trader_settings": {
            "min_self_funds": 100,
            "min_copy_funds": 1000,
            "trading_strategy": {
                "type": "order_based",
            },
        },
    }


@pytest.fixture
def trader_create_payload(sample_config):
    """Valid payload for creating a trader."""
    return {
        "wallet_address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a",
        "private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        "config": sample_config,
        "name": "Test Trader",
        "description": "Test description",
    }


@pytest.fixture
def mock_trader_full(mock_user):
    """Mock trader with all required fields."""
    trader = MagicMock()
    trader.id = str(uuid.uuid4())
    trader.user_id = mock_user.id
    trader.wallet_address = "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"
    trader.runtime_name = "trader-e221ef33"
    trader.status = "configured"
    trader.image_tag = "latest"
    trader.created_at = datetime.now(UTC)
    trader.updated_at = datetime.now(UTC)
    trader.start_attempts = 0
    trader.last_error = None
    trader.stopped_at = None
    trader.name = "Test Trader"
    trader.description = "Test description"

    # Mock latest_config
    mock_config = MagicMock()
    mock_config.config_json = {
        "provider_settings": {
            "exchange": "hyperliquid",
            "network": "mainnet",
            "self_account": {"address": "0xe221ef33a07bcf16bde86a5dc6d7c85ebc3a1f9a"},
            "copy_account": {"address": "0x1234567890abcdef1234567890abcdef12345678"},
        },
        "trader_settings": {
            "min_self_funds": 100,
            "min_copy_funds": 1000,
            "trading_strategy": {"type": "order_based"},
        },
    }
    trader.latest_config = mock_config

    return trader


class TestCreateTraderEndpoint:
    """Tests for POST /api/v1/traders/"""

    def test_create_trader_success(
        self, auth_client, mock_db, mock_user, mock_trader_full, trader_create_payload
    ):
        """Test successful trader creation returns 201."""
        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.create_trader.return_value = mock_trader_full

            response = auth_client.post("/api/v1/traders/", json=trader_create_payload)

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == mock_trader_full.id
            assert data["wallet_address"] == mock_trader_full.wallet_address
            assert data["runtime_name"] == mock_trader_full.runtime_name
            assert data["status"] == mock_trader_full.status
            assert data["name"] == mock_trader_full.name
            assert data["description"] == mock_trader_full.description
            assert data["latest_config"] is not None

    def test_create_trader_invalid_wallet(
        self, auth_client, mock_db, mock_user, trader_create_payload
    ):
        """Test invalid wallet address returns 422."""
        # Invalid wallet address (too short)
        invalid_payload = trader_create_payload.copy()
        invalid_payload["wallet_address"] = "0xinvalid"

        response = auth_client.post("/api/v1/traders/", json=invalid_payload)

        # Pydantic validation error
        assert response.status_code == 422

    def test_create_trader_value_error(
        self, auth_client, mock_db, mock_user, trader_create_payload
    ):
        """Test ValueError from service returns 400."""
        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.create_trader.side_effect = ValueError(
                "Copy account cannot be the same as self account"
            )

            response = auth_client.post("/api/v1/traders/", json=trader_create_payload)

            assert response.status_code == 400
            assert "Copy account cannot be the same" in response.json()["detail"]

    def test_create_trader_service_error(
        self, auth_client, mock_db, mock_user, trader_create_payload
    ):
        """Test TraderServiceError returns 500."""
        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.create_trader.side_effect = TraderServiceError("Docker connection failed")

            response = auth_client.post("/api/v1/traders/", json=trader_create_payload)

            assert response.status_code == 500
            assert "Failed to deploy trader" in response.json()["detail"]


class TestStartTraderEndpoint:
    """Tests for POST /api/v1/traders/{id}/start"""

    def test_start_trader_success(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test successful start returns 200 with running status."""
        trader_id = mock_trader_full.id
        mock_trader_full.status = "running"
        mock_trader_full.start_attempts = 1

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.start_trader.return_value = mock_trader_full

            response = auth_client.post(f"/api/v1/traders/{trader_id}/start")

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Trader started successfully"
            assert data["trader_id"] == trader_id
            assert data["runtime_name"] == mock_trader_full.runtime_name
            assert data["status"] == "running"
            assert data["start_attempts"] == 1

    def test_start_trader_invalid_state(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test start from invalid state returns 400."""
        trader_id = mock_trader_full.id

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.start_trader.side_effect = ValueError(
                "Cannot start trader in state: running"
            )

            response = auth_client.post(f"/api/v1/traders/{trader_id}/start")

            assert response.status_code == 400
            assert "Cannot start trader" in response.json()["detail"]

    def test_start_trader_not_found(self, auth_client, mock_db, mock_user):
        """Test start non-existent trader returns 404."""
        trader_id = str(uuid.uuid4())

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.start_trader.side_effect = TraderNotFoundError("Trader not found")

            response = auth_client.post(f"/api/v1/traders/{trader_id}/start")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_start_trader_ownership_error(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test start trader owned by another user returns 403."""
        trader_id = mock_trader_full.id

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.start_trader.side_effect = TraderOwnershipError(
                "You do not own this trader"
            )

            response = auth_client.post(f"/api/v1/traders/{trader_id}/start")

            assert response.status_code == 403
            assert "access" in response.json()["detail"].lower()

    def test_start_trader_service_error_returns_status(
        self, auth_client, mock_db, mock_user, mock_trader_full
    ):
        """Test TraderServiceError during start returns trader status with error message."""
        trader_id = mock_trader_full.id
        mock_trader_full.status = "failed"
        mock_trader_full.start_attempts = 3

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.start_trader.side_effect = TraderServiceError(
                "Docker service creation failed"
            )
            mock_service.get_trader.return_value = mock_trader_full

            response = auth_client.post(f"/api/v1/traders/{trader_id}/start")

            # Start endpoint returns 200 even on service error to show current status
            assert response.status_code == 200
            data = response.json()
            assert "Failed to start trader" in data["message"]
            assert data["status"] == "failed"
            assert data["start_attempts"] == 3


class TestStopTraderEndpoint:
    """Tests for POST /api/v1/traders/{id}/stop"""

    def test_stop_trader_success(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test successful stop returns 200 with stopped status."""
        trader_id = mock_trader_full.id
        mock_trader_full.status = "stopped"

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.stop_trader.return_value = mock_trader_full

            response = auth_client.post(f"/api/v1/traders/{trader_id}/stop")

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Trader stopped successfully"
            assert data["trader_id"] == trader_id
            assert data["runtime_name"] == mock_trader_full.runtime_name
            assert data["status"] == "stopped"

    def test_stop_trader_not_found(self, auth_client, mock_db, mock_user):
        """Test stop non-existent trader returns 404."""
        trader_id = str(uuid.uuid4())

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.stop_trader.side_effect = TraderNotFoundError("Trader not found")

            response = auth_client.post(f"/api/v1/traders/{trader_id}/stop")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_stop_trader_invalid_state(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test stop from invalid state returns 400."""
        trader_id = mock_trader_full.id

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.stop_trader.side_effect = ValueError(
                "Cannot stop trader in state: configured"
            )

            response = auth_client.post(f"/api/v1/traders/{trader_id}/stop")

            assert response.status_code == 400
            assert "Cannot stop trader" in response.json()["detail"]

    def test_stop_trader_ownership_error(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test stop trader owned by another user returns 403."""
        trader_id = mock_trader_full.id

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.stop_trader.side_effect = TraderOwnershipError(
                "You do not own this trader"
            )

            response = auth_client.post(f"/api/v1/traders/{trader_id}/stop")

            assert response.status_code == 403
            assert "access" in response.json()["detail"].lower()

    def test_stop_trader_service_error(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test TraderServiceError during stop returns 500."""
        trader_id = mock_trader_full.id

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.stop_trader.side_effect = TraderServiceError(
                "Docker service removal failed"
            )

            response = auth_client.post(f"/api/v1/traders/{trader_id}/stop")

            assert response.status_code == 500
            assert "Failed to stop trader" in response.json()["detail"]


class TestUpdateTraderInfoEndpoint:
    """Tests for PATCH /api/v1/traders/{id}"""

    def test_update_info_success(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test successful update returns 200 with new values."""
        trader_id = mock_trader_full.id
        mock_trader_full.name = "Updated Name"
        mock_trader_full.description = "Updated description"

        update_payload = {
            "name": "Updated Name",
            "description": "Updated description",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader_info.return_value = mock_trader_full

            response = auth_client.patch(f"/api/v1/traders/{trader_id}", json=update_payload)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Updated Name"
            assert data["description"] == "Updated description"
            assert data["id"] == trader_id

    def test_update_info_duplicate_name(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test duplicate name returns 409."""
        trader_id = mock_trader_full.id

        update_payload = {
            "name": "Existing Name",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader_info.side_effect = ValueError(
                "Trader name already exists for this user"
            )

            response = auth_client.patch(f"/api/v1/traders/{trader_id}", json=update_payload)

            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]

    def test_update_info_not_found(self, auth_client, mock_db, mock_user):
        """Test update non-existent trader returns 404."""
        trader_id = str(uuid.uuid4())

        update_payload = {
            "name": "New Name",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader_info.side_effect = TraderNotFoundError("Trader not found")

            response = auth_client.patch(f"/api/v1/traders/{trader_id}", json=update_payload)

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_update_info_ownership_error(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test update trader owned by another user returns 403."""
        trader_id = mock_trader_full.id

        update_payload = {
            "name": "New Name",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader_info.side_effect = TraderOwnershipError(
                "You do not own this trader"
            )

            response = auth_client.patch(f"/api/v1/traders/{trader_id}", json=update_payload)

            assert response.status_code == 403
            assert "access" in response.json()["detail"].lower()

    def test_update_info_partial_update(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test partial update with only name."""
        trader_id = mock_trader_full.id
        mock_trader_full.name = "Only Name Updated"

        update_payload = {
            "name": "Only Name Updated",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader_info.return_value = mock_trader_full

            response = auth_client.patch(f"/api/v1/traders/{trader_id}", json=update_payload)

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "Only Name Updated"


class TestUpdateTraderConfigEndpoint:
    """Tests for PATCH /api/v1/traders/{id}/config"""

    def test_update_config_success(
        self, auth_client, mock_db, mock_user, mock_trader_full, sample_config
    ):
        """Test successful config update returns 200."""
        trader_id = mock_trader_full.id

        # Update config with new values
        updated_config = sample_config.copy()
        updated_config["trader_settings"]["min_self_funds"] = 200
        mock_trader_full.latest_config.config_json = updated_config

        update_payload = {
            "config": updated_config,
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader.return_value = mock_trader_full

            response = auth_client.patch(f"/api/v1/traders/{trader_id}/config", json=update_payload)

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == trader_id
            assert data["latest_config"]["trader_settings"]["min_self_funds"] == 200

    def test_update_config_value_error(
        self, auth_client, mock_db, mock_user, mock_trader_full, sample_config
    ):
        """Test ValueError from config validation returns 400."""
        trader_id = mock_trader_full.id

        update_payload = {
            "config": sample_config,
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader.side_effect = ValueError(
                "Assets cannot be both allowed and blocked"
            )

            response = auth_client.patch(f"/api/v1/traders/{trader_id}/config", json=update_payload)

            assert response.status_code == 400
            assert "cannot be both" in response.json()["detail"]

    def test_update_config_not_found(self, auth_client, mock_db, mock_user, sample_config):
        """Test update config for non-existent trader returns 404."""
        trader_id = str(uuid.uuid4())

        update_payload = {
            "config": sample_config,
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader.side_effect = TraderNotFoundError("Trader not found")

            response = auth_client.patch(f"/api/v1/traders/{trader_id}/config", json=update_payload)

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_update_config_ownership_error(
        self, auth_client, mock_db, mock_user, mock_trader_full, sample_config
    ):
        """Test update config for trader owned by another user returns 403."""
        trader_id = mock_trader_full.id

        update_payload = {
            "config": sample_config,
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader.side_effect = TraderOwnershipError(
                "You do not own this trader"
            )

            response = auth_client.patch(f"/api/v1/traders/{trader_id}/config", json=update_payload)

            assert response.status_code == 403
            assert "access" in response.json()["detail"].lower()

    def test_update_config_service_error(
        self, auth_client, mock_db, mock_user, mock_trader_full, sample_config
    ):
        """Test TraderServiceError during config update returns 500."""
        trader_id = mock_trader_full.id

        update_payload = {
            "config": sample_config,
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_trader.side_effect = TraderServiceError(
                "Failed to restart container with new config"
            )

            response = auth_client.patch(f"/api/v1/traders/{trader_id}/config", json=update_payload)

            assert response.status_code == 500
            assert "Failed to update trader" in response.json()["detail"]


class TestUpdateTraderImage:
    """Tests for POST /api/v1/traders/{id}/update-image"""

    def test_update_image_success_running_trader(
        self, auth_client, mock_db, mock_user, mock_trader_full
    ):
        """Test successful image update for running trader returns 200 with updated image_tag."""
        trader_id = mock_trader_full.id
        mock_trader_full.status = "running"
        mock_trader_full.image_tag = "0.4.4"

        update_payload = {
            "new_tag": "0.4.4",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_image.return_value = mock_trader_full

            response = auth_client.post(
                f"/api/v1/traders/{trader_id}/update-image", json=update_payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == trader_id
            assert data["image_tag"] == "0.4.4"
            assert data["status"] == "running"

    def test_update_image_success_stopped_trader(
        self, auth_client, mock_db, mock_user, mock_trader_full
    ):
        """Test successful image update for stopped trader returns 200."""
        trader_id = mock_trader_full.id
        mock_trader_full.status = "stopped"
        mock_trader_full.image_tag = "0.5.0"

        update_payload = {
            "new_tag": "0.5.0",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_image.return_value = mock_trader_full

            response = auth_client.post(
                f"/api/v1/traders/{trader_id}/update-image", json=update_payload
            )

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == trader_id
            assert data["image_tag"] == "0.5.0"
            assert data["status"] == "stopped"

    def test_update_image_trader_not_found(self, auth_client, mock_db, mock_user):
        """Test update image for non-existent trader returns 404."""
        trader_id = str(uuid.uuid4())

        update_payload = {
            "new_tag": "0.4.4",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_image.side_effect = TraderNotFoundError("Trader not found")

            response = auth_client.post(
                f"/api/v1/traders/{trader_id}/update-image", json=update_payload
            )

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_update_image_ownership_error(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test update image for trader owned by another user returns 403."""
        trader_id = mock_trader_full.id

        update_payload = {
            "new_tag": "0.4.4",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_image.side_effect = TraderOwnershipError(
                "You do not own this trader"
            )

            response = auth_client.post(
                f"/api/v1/traders/{trader_id}/update-image", json=update_payload
            )

            assert response.status_code == 403
            assert "access denied" in response.json()["detail"].lower()

    def test_update_image_service_error(self, auth_client, mock_db, mock_user, mock_trader_full):
        """Test TraderServiceError during image update returns 500."""
        trader_id = mock_trader_full.id

        update_payload = {
            "new_tag": "0.4.4",
        }

        with patch("hyper_trader_api.routers.traders.TraderService") as MockService:
            mock_service = MockService.return_value
            mock_service.update_image.side_effect = TraderServiceError(
                "Failed to pull image or update service"
            )

            response = auth_client.post(
                f"/api/v1/traders/{trader_id}/update-image", json=update_payload
            )

            assert response.status_code == 500
            assert "Failed to pull image" in response.json()["detail"]

    def test_update_image_unauthorized(self, client, mock_db):
        """Test update image without authentication returns 401."""
        trader_id = str(uuid.uuid4())

        update_payload = {
            "new_tag": "0.4.4",
        }

        response = client.post(f"/api/v1/traders/{trader_id}/update-image", json=update_payload)

        assert response.status_code == 401
