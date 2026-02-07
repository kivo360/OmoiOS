"""
Integration tests for sandbox message endpoints.
These verify the FULL flow, not just HTTP status codes.

Phase 2.3 from implementation checklist.
"""

import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient


@pytest.mark.integration
class TestMessageQueueEndpoint:
    """Integration tests for POST/GET /sandboxes/{id}/messages."""

    def test_endpoint_exists_and_accepts_valid_message(
        self, client: TestClient, sample_message: dict
    ):
        """
        INTEGRATION: POST /sandboxes/{id}/messages should accept valid messages.

        This is the FIRST test - if this fails, nothing else matters.
        """
        sandbox_id = "test-message-endpoint"

        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json=sample_message,
        )

        # VERIFY: Endpoint exists and accepts POST
        assert (
            response.status_code == 200
        ), f"Got {response.status_code}: {response.text}"

        # VERIFY: Response has required fields
        data = response.json()
        assert data["status"] == "queued"
        assert data["sandbox_id"] == sandbox_id
        assert "message_id" in data

    def test_message_queue_roundtrip(self, client: TestClient, sample_message: dict):
        """
        SPEC: POST message → GET messages returns it.

        This validates the message queue mechanism independent of workers.
        """
        sandbox_id = "test-message-roundtrip"

        # 1. Queue a message
        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json=sample_message,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "queued"

        # 2. Retrieve message
        response = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        assert response.status_code == 200
        messages = response.json()

        assert len(messages) == 1
        assert messages[0]["content"] == sample_message["content"]
        assert messages[0]["message_type"] == sample_message["message_type"]

        # 3. Messages should be cleared after retrieval
        response = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        assert response.json() == []

    def test_message_queue_fifo_order(self, client: TestClient):
        """SPEC: Messages should be returned in FIFO order."""
        sandbox_id = "test-message-fifo"

        # Queue multiple messages
        for i in range(3):
            client.post(
                f"/api/v1/sandboxes/{sandbox_id}/messages",
                json={"content": f"Message {i}", "message_type": "user_message"},
            )

        # Retrieve and verify order
        response = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages")
        messages = response.json()

        assert len(messages) == 3
        assert messages[0]["content"] == "Message 0"
        assert messages[1]["content"] == "Message 1"
        assert messages[2]["content"] == "Message 2"

    def test_invalid_message_is_rejected(self, client: TestClient):
        """INTEGRATION: Invalid message should be rejected with 422."""
        sandbox_id = "test-invalid-message"

        # Missing required field
        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json={"message_type": "user_message"},  # missing content
        )

        assert response.status_code == 422


@pytest.mark.integration
class TestMessageTypes:
    """Integration tests for different message types."""

    def test_interrupt_message_type(self, client: TestClient):
        """SPEC: "interrupt" message type should be supported."""
        sandbox_id = "test-interrupt"

        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json={"content": "STOP", "message_type": "interrupt"},
        )
        assert response.status_code == 200

        messages = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages").json()
        assert messages[0]["message_type"] == "interrupt"

    def test_guardian_nudge_message_type(self, client: TestClient):
        """SPEC: "guardian_nudge" message type should be supported."""
        sandbox_id = "test-guardian"

        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json={"content": "Consider edge cases", "message_type": "guardian_nudge"},
        )
        assert response.status_code == 200

        messages = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages").json()
        assert messages[0]["message_type"] == "guardian_nudge"

    def test_system_message_type(self, client: TestClient):
        """SPEC: "system" message type should be supported."""
        sandbox_id = "test-system"

        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/messages",
            json={"content": "Time limit warning", "message_type": "system"},
        )
        assert response.status_code == 200

        messages = client.get(f"/api/v1/sandboxes/{sandbox_id}/messages").json()
        assert messages[0]["message_type"] == "system"


@pytest.mark.integration
@pytest.mark.requires_redis
class TestMessageEventBroadcast:
    """Integration tests that verify message events reach subscribers."""

    def test_message_is_broadcast_to_event_bus(
        self, client: TestClient, sample_message: dict
    ):
        """
        INTEGRATION: Posting a message should publish to EventBus.

        The message queue should notify subscribers that a new message is pending.
        """
        sandbox_id = "test-message-broadcast"

        with patch("omoi_os.api.routes.sandbox.get_event_bus") as mock_get_bus:
            mock_bus = MagicMock()
            mock_get_bus.return_value = mock_bus

            response = client.post(
                f"/api/v1/sandboxes/{sandbox_id}/messages",
                json=sample_message,
            )
            assert response.status_code == 200

            # VERIFY: EventBus.publish was called
            mock_bus.publish.assert_called_once()

            # VERIFY: Event has correct structure
            call_args = mock_bus.publish.call_args[0][0]
            assert call_args.event_type == "SANDBOX_MESSAGE_QUEUED"
            assert call_args.entity_type == "sandbox"
            assert call_args.entity_id == sandbox_id


@pytest.mark.integration
class TestMessageIsolation:
    """Tests that verify messages are isolated by sandbox_id."""

    def test_messages_are_isolated_by_sandbox_id(self, client: TestClient):
        """Messages for sandbox A should NOT appear in sandbox B."""
        sandbox_a = "isolation-sandbox-a"
        sandbox_b = "isolation-sandbox-b"

        # Post to sandbox A
        client.post(
            f"/api/v1/sandboxes/{sandbox_a}/messages",
            json={"content": "Message for A", "message_type": "user_message"},
        )

        # Post to sandbox B
        client.post(
            f"/api/v1/sandboxes/{sandbox_b}/messages",
            json={"content": "Message for B", "message_type": "user_message"},
        )

        # VERIFY: Each sandbox only sees its own messages
        a_messages = client.get(f"/api/v1/sandboxes/{sandbox_a}/messages").json()
        b_messages = client.get(f"/api/v1/sandboxes/{sandbox_b}/messages").json()

        assert len(a_messages) == 1
        assert a_messages[0]["content"] == "Message for A"
        assert len(b_messages) == 1
        assert b_messages[0]["content"] == "Message for B"
