"""
Pytest fixtures for HyperTrader API tests.

Uses mocks instead of real database connections.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock the database engine and lifespan BEFORE importing the app
with patch("hyper_trader_api.database.engine") as mock_engine:
    mock_engine.connect.return_value.__enter__.return_value.execute.return_value = None
    mock_engine.dispose.return_value = None

    # Mock the reconciliation workers
    with (
        patch("hyper_trader_api.main.start_reconciliation"),
        patch("hyper_trader_api.main.stop_reconciliation"),
    ):
        from hyper_trader_api.database import get_db
        from hyper_trader_api.main import app


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def client(mock_db):
    """Test client with mocked database."""

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    # Mock the engine for health checks
    with patch("hyper_trader_api.main.engine") as mock_engine:
        mock_engine.connect.return_value.__enter__.return_value.execute.return_value = None
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Mock user object."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.plan_tier = "free"
    user.is_admin = False
    user.password_hash = "hashed_password"
    user.api_key_hash = None
    user.created_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_trader(mock_user):
    """Mock trader object."""
    trader = MagicMock()
    trader.id = uuid.uuid4()
    trader.user_id = mock_user.id
    trader.wallet_address = "0x1234567890123456789012345678901234567890"
    trader.k8s_name = "trader-12345678"
    trader.status = "running"
    trader.image_tag = "latest"
    trader.created_at = datetime.now(UTC)
    trader.updated_at = datetime.now(UTC)
    trader.latest_config = MagicMock()
    trader.latest_config.config_json = {"name": "Test Trader", "exchange": "hyperliquid"}
    return trader


@pytest.fixture
def mock_tokens():
    """Mock JWT tokens."""
    return {
        "access_token": "mock_access_token",
        "refresh_token": "mock_refresh_token",
    }


@pytest.fixture
def auth_headers():
    """Authorization headers with mock token."""
    return {"Authorization": "Bearer mock_access_token"}
