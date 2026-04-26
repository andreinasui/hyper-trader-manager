"""Tests for the /health endpoint."""
from importlib.metadata import version

from fastapi.testclient import TestClient


def test_health_version_matches_package_version(client: TestClient) -> None:
    """Health endpoint version must match the installed package version."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    expected_base = version("hyper-trader-api")
    # In test env, environment defaults to "development" so -dev suffix expected
    assert data["version"].startswith(expected_base)


def test_health_returns_expected_fields(client: TestClient) -> None:
    """Health endpoint must return status, database, and version fields."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0
