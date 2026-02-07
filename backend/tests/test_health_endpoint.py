"""Tests for the /health endpoint."""

import pytest
from fastapi.testclient import TestClient

from omoi_os.api.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test the /health endpoint."""

    def test_health_endpoint_returns_status_and_version(self, client: TestClient):
        """Test that /health endpoint returns both status and version."""
        response = client.get("/health")

        # Should return 200 OK
        assert response.status_code == 200

        # Should return JSON with status and version
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    def test_health_endpoint_content_type(self, client: TestClient):
        """Test that /health endpoint returns correct content type."""
        response = client.get("/health")

        # Should return application/json
        assert response.headers["content-type"] == "application/json"
