"""Tests for the Hello World API endpoint.

This tests the simple /api/v1/hello endpoint that returns a greeting.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestHelloEndpoint:
    """Tests for the /api/v1/hello endpoint."""

    def test_hello_returns_greeting(self, client: TestClient):
        """Test that GET /api/v1/hello returns a hello world message."""
        response = client.get("/api/v1/hello")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Hello, World!"
        assert "timestamp" in data
        assert data["version"] == "0.1.0"

    def test_hello_personalized(self, client: TestClient):
        """Test that GET /api/v1/hello/{name} returns personalized greeting."""
        response = client.get("/api/v1/hello/Alice")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Hello, Alice!"
        assert data["name"] == "Alice"
        assert "timestamp" in data

    def test_hello_with_special_characters(self, client: TestClient):
        """Test hello with URL-encoded name."""
        response = client.get("/api/v1/hello/John%20Doe")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Hello, John Doe!"
        assert data["name"] == "John Doe"

    def test_hello_timestamp_format(self, client: TestClient):
        """Test that timestamp is in ISO format."""
        from datetime import datetime

        response = client.get("/api/v1/hello")

        assert response.status_code == 200
        data = response.json()
        # Should be parseable as ISO datetime
        timestamp = datetime.fromisoformat(data["timestamp"])
        assert timestamp is not None
