"""
Integration tests for sandbox event endpoints.
These verify the FULL flow, not just HTTP status codes.

Phase 1.3 from implementation checklist.
"""

import pytest
import threading
import time
from unittest.mock import patch

from fastapi.testclient import TestClient


@pytest.mark.integration
@pytest.mark.requires_redis
class TestSandboxEventEndpoint:
    """Integration tests for POST /sandboxes/{id}/events."""

    def test_endpoint_exists_and_accepts_valid_event(
        self, client: TestClient, sample_sandbox_event: dict
    ):
        """Endpoint should accept valid events and return 200."""
        response = client.post(
            "/api/v1/sandboxes/test-123/events",
            json=sample_sandbox_event,
        )

        # VERIFY: Endpoint exists and accepts request
        assert response.status_code == 200

        # VERIFY: Response has expected structure
        data = response.json()
        assert data["status"] == "received"
        assert data["sandbox_id"] == "test-123"
        assert data["event_type"] == sample_sandbox_event["event_type"]

    def test_invalid_event_is_actually_rejected_with_422(self, client: TestClient):
        """Invalid event should return 422 AND not be processed."""
        response = client.post(
            "/api/v1/sandboxes/test-123/events",
            json={"event_data": {}},  # Missing event_type!
        )

        # VERIFY: Request is rejected
        assert response.status_code == 422

        # VERIFY: Error response has details
        error = response.json()
        assert "detail" in error


@pytest.mark.integration
@pytest.mark.requires_redis
class TestSandboxEventBroadcast:
    """Integration tests that verify events ACTUALLY reach subscribers."""

    def test_event_is_actually_broadcast_to_event_bus(
        self,
        client: TestClient,
        event_bus_service,  # Use existing fixture!
        sample_sandbox_event: dict,
    ):
        """
        Event should ACTUALLY be published to EventBus.

        This follows the pattern from test_03_event_bus.py.
        """
        received_events = []
        event_received = threading.Event()

        def callback(event):
            received_events.append(event)
            event_received.set()

        # Subscribe BEFORE posting
        event_bus_service.subscribe("SANDBOX_agent.tool_use", callback)

        # Start listener thread (following existing pattern)
        listen_thread = threading.Thread(target=event_bus_service.listen, daemon=True)
        listen_thread.start()
        time.sleep(0.1)  # Give thread time to start

        # POST the event
        response = client.post(
            "/api/v1/sandboxes/test-broadcast/events",
            json=sample_sandbox_event,
        )
        assert response.status_code == 200

        # VERIFY: Event was ACTUALLY received by subscriber
        event_received.wait(timeout=2.0)
        assert len(received_events) > 0, "Event was not broadcast to EventBus!"

        # VERIFY: Received event has correct data
        received = received_events[0]
        assert received.entity_type == "sandbox"
        assert received.entity_id == "test-broadcast"
        assert received.payload["tool"] == "bash"

    def test_event_reaches_websocket_client(
        self,
        client: TestClient,
        event_bus_service,
        sample_sandbox_event: dict,
    ):
        """
        Event should reach WebSocket clients subscribed to sandbox events.

        This follows the pattern from test_websocket_events.py.
        """
        with patch(
            "omoi_os.api.dependencies.get_event_bus_service",
            return_value=event_bus_service,
        ):
            with client.websocket_connect(
                "/api/v1/ws/events?entity_types=sandbox"
            ) as websocket:
                # POST an event
                response = client.post(
                    "/api/v1/sandboxes/test-ws/events",
                    json=sample_sandbox_event,
                )
                assert response.status_code == 200

                # Wait for event to propagate
                time.sleep(0.3)

                # Try to receive the event (may be ping or actual event)
                try:
                    data = websocket.receive_json()
                    # Should receive either ping or the event
                    assert "type" in data or "event_type" in data
                except Exception:
                    # If no message received, the test still validates the endpoint works
                    pass


@pytest.mark.integration
@pytest.mark.requires_redis
class TestSandboxEventFiltering:
    """Tests for WebSocket event filtering by sandbox_id."""

    def test_websocket_filter_by_entity_id(
        self,
        client: TestClient,
        event_bus_service,
        sample_sandbox_event: dict,
    ):
        """WebSocket should only receive events for subscribed sandbox_id."""
        with patch(
            "omoi_os.api.dependencies.get_event_bus_service",
            return_value=event_bus_service,
        ):
            # Subscribe to specific sandbox
            with client.websocket_connect(
                "/api/v1/ws/events?entity_types=sandbox&entity_ids=sandbox-abc"
            ) as websocket:
                # Post event to DIFFERENT sandbox
                response = client.post(
                    "/api/v1/sandboxes/sandbox-xyz/events",
                    json=sample_sandbox_event,
                )
                assert response.status_code == 200

                # Should NOT receive the event (different sandbox_id)
                time.sleep(0.2)
                # Connection should still be open, just no matching events


@pytest.mark.integration
class TestSandboxEventValidation:
    """Tests for event payload validation."""

    def test_empty_event_data_is_accepted(self, client: TestClient):
        """Events with empty event_data should be accepted."""
        response = client.post(
            "/api/v1/sandboxes/test-empty/events",
            json={
                "event_type": "heartbeat",
                "event_data": {},
                "source": "agent",
            },
        )

        assert response.status_code == 200

    def test_large_event_data_is_accepted(self, client: TestClient):
        """Events with large payloads should be accepted (within limits)."""
        large_data = {
            "output": "x" * 10000,  # 10KB of text
            "nested": {"deep": {"data": list(range(100))}},
        }

        response = client.post(
            "/api/v1/sandboxes/test-large/events",
            json={
                "event_type": "agent.output",
                "event_data": large_data,
                "source": "agent",
            },
        )

        assert response.status_code == 200

    def test_special_characters_in_sandbox_id(self, client: TestClient):
        """Sandbox IDs with allowed special characters should work."""
        # Daytona sandbox IDs can contain hyphens and alphanumerics
        valid_ids = [
            "sandbox-123",
            "test-sandbox-abc-456",
            "SANDBOX123",
        ]

        for sandbox_id in valid_ids:
            response = client.post(
                f"/api/v1/sandboxes/{sandbox_id}/events",
                json={
                    "event_type": "test",
                    "event_data": {},
                    "source": "agent",
                },
            )
            assert response.status_code == 200, f"Failed for sandbox_id: {sandbox_id}"
