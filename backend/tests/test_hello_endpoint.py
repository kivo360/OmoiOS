"""Tests for the /hello greeting endpoint."""

import pytest
from fastapi.testclient import TestClient

from omoi_os.api.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


class TestHelloEndpoint:
    """Test the /hello greeting endpoint."""

    def test_hello_endpoint_returns_greeting_message(self, client: TestClient):
        """Test that /hello endpoint returns a greeting message."""
        response = client.get("/hello")

        # Should return 200 OK
        assert response.status_code == 200

        # Should return JSON with message
        data = response.json()
        assert "message" in data
        assert "Hello" in data["message"]
        assert "OmoiOS" in data["message"]

    def test_hello_endpoint_content_type(self, client: TestClient):
        """Test that /hello endpoint returns correct content type."""
        response = client.get("/hello")

        # Should return application/json
        assert response.headers["content-type"] == "application/json"
