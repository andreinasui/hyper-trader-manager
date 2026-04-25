"""
Tests for images router endpoints.

Tests for image version information:
- GET /api/v1/images
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def images_client(mock_db):
    """Test client with images router registered."""
    from fastapi import FastAPI

    from hyper_trader_api.database import get_db
    from hyper_trader_api.routers.images import router as images_router

    # Create test app with only the images router
    app = FastAPI()
    app.include_router(images_router)

    # Override database dependency
    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(images_client, mock_user):
    """Test client with authentication override."""
    from hyper_trader_api.middleware.session_auth import get_current_user

    app = images_client.app
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield images_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_image_versions():
    """Sample image version information."""
    return {
        "latest_local": "0.4.3",
        "all_local": ["0.4.3", "0.4.2"],
        "latest_remote": "0.4.4",
        "all_remote": ["0.4.4", "0.4.3", "0.4.2"],
    }


class TestGetImageVersions:
    """Tests for GET /api/v1/images endpoint."""

    @patch("hyper_trader_api.routers.images.ImageService")
    def test_get_image_versions_success(
        self, mock_image_service, auth_client, sample_image_versions
    ):
        """Test successful retrieval of image versions."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_image_versions.return_value = MagicMock(**sample_image_versions)
        mock_image_service.return_value = mock_service_instance

        response = auth_client.get("/api/v1/images")

        assert response.status_code == 200
        data = response.json()
        assert data["latest_local"] == "0.4.3"
        assert data["latest_remote"] == "0.4.4"
        assert len(data["all_local"]) == 2
        assert len(data["all_remote"]) == 3

        mock_service_instance.get_image_versions.assert_called_once_with()

    @patch("hyper_trader_api.routers.images.ImageService")
    def test_get_image_versions_no_remote(self, mock_image_service, auth_client):
        """Test image versions when remote fetch returns nothing."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_image_versions.return_value = MagicMock(
            latest_local="0.4.3",
            all_local=["0.4.3", "0.4.2"],
            latest_remote=None,
            all_remote=[],
        )
        mock_image_service.return_value = mock_service_instance

        response = auth_client.get("/api/v1/images")

        assert response.status_code == 200
        data = response.json()
        assert data["latest_local"] == "0.4.3"
        assert data["latest_remote"] is None
        assert data["all_remote"] == []

    def test_get_image_versions_unauthorized(self, images_client):
        """Test image versions retrieval fails without authentication."""
        response = images_client.get("/api/v1/images")

        assert response.status_code == 401
        assert "authorization" in response.json()["detail"].lower()

    def test_get_image_versions_with_invalid_token_header(self, images_client):
        """Test image versions retrieval fails with invalid auth header."""
        response = images_client.get("/api/v1/images", headers={"Authorization": "InvalidFormat"})

        assert response.status_code == 401

    @patch("hyper_trader_api.routers.images.ImageService")
    def test_get_image_versions_empty(self, mock_image_service, auth_client):
        """Test image versions when no images exist locally or remotely."""
        mock_service_instance = MagicMock()
        mock_service_instance.get_image_versions.return_value = MagicMock(
            latest_local=None,
            all_local=[],
            latest_remote=None,
            all_remote=[],
        )
        mock_image_service.return_value = mock_service_instance

        response = auth_client.get("/api/v1/images")

        assert response.status_code == 200
        data = response.json()
        assert data["latest_local"] is None
        assert data["latest_remote"] is None
        assert data["all_local"] == []
        assert data["all_remote"] == []
