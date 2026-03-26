"""
Pytest fixtures for HyperTrader API tests.

Uses mocks and environment variables to avoid database connection issues
during test collection.
"""

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

# Set a valid DATABASE_URL before any imports that might load config
# This prevents SQLAlchemy URL parsing errors during collection
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def client(mock_db):
    """Test client with mocked database."""
    # Import here to use the patched environment
    from fastapi.testclient import TestClient

    from hyper_trader_api.database import get_db
    from hyper_trader_api.main import app

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
    """Mock user object for local auth."""
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.username = "testuser"
    user.is_admin = False
    user.created_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_admin_user():
    """Mock admin user object for local auth."""
    user = MagicMock()
    user.id = str(uuid.uuid4())
    user.username = "admin"
    user.is_admin = True
    user.created_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_trader(mock_user):
    """Mock trader object."""
    trader = MagicMock()
    trader.id = str(uuid.uuid4())
    trader.user_id = mock_user.id
    trader.runtime_name = "trader-12345678"
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
    }


@pytest.fixture
def auth_headers():
    """Authorization headers with mock token."""
    return {"Authorization": "Bearer mock_access_token"}
