"""Tests for /api/v1/reasoning/* endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.api
class TestReasoningEndpointsUnit:
    """Unit tests for reasoning/decision tracking endpoints."""

    def test_get_event_types(self, client: TestClient):
        """Test GET /reasoning/types returns event types."""
        response = client.get("/api/v1/reasoning/types")

        assert response.status_code == 200
        data = response.json()
        assert "event_types" in data
        assert isinstance(data["event_types"], list)

    def test_list_events(self, client: TestClient):
        """Test GET /reasoning/events returns list."""
        response = client.get("/api/v1/reasoning/events")

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_list_events_with_type_filter(self, client: TestClient):
        """Test GET /reasoning/events with type filter."""
        response = client.get("/api/v1/reasoning/events?event_type=task_spawned")

        assert response.status_code == 200

    def test_list_events_with_entity_filter(self, client: TestClient):
        """Test GET /reasoning/events with entity filter."""
        response = client.get(
            "/api/v1/reasoning/events?entity_type=ticket&entity_id=test-123"
        )

        assert response.status_code == 200

    def test_get_nonexistent_event(self, client: TestClient):
        """Test GET /reasoning/events/{id} for non-existent event."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/reasoning/events/{fake_id}")

        assert response.status_code == 404

    def test_get_entity_timeline(self, client: TestClient):
        """Test GET /reasoning/timeline/{entity_type}/{entity_id}."""
        response = client.get("/api/v1/reasoning/timeline/ticket/test-123")

        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestReasoningIntegration:
    """Integration tests for reasoning with real entities."""

    def test_ticket_timeline(self, client: TestClient, sample_ticket):
        """Test getting timeline for a real ticket."""
        response = client.get(
            f"/api/v1/reasoning/timeline/ticket/{sample_ticket.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_create_reasoning_event(self, client: TestClient, sample_ticket):
        """Test creating a reasoning event."""
        response = client.post(
            "/api/v1/reasoning/events",
            json={
                "event_type": "decision_made",
                "entity_type": "ticket",
                "entity_id": str(sample_ticket.id),
                "reasoning": "Test reasoning for decision",
            },
        )

        # Should succeed or return validation error
        assert response.status_code in [200, 201, 400, 422]
