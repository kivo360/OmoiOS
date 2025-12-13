"""
Unit tests for message queue internal logic.
These test the functions, NOT the HTTP layer.

Phase 2.1 from implementation checklist.
"""

import pytest
from unittest.mock import MagicMock


@pytest.mark.unit
class TestMessageQueueStorage:
    """Test in-memory message queue data structure."""

    def test_queue_stores_message_correctly(self):
        """UNIT: Message should be stored with all fields."""
        from omoi_os.api.routes.sandbox import MessageQueue

        queue = MessageQueue()

        queue.enqueue(
            sandbox_id="test-sandbox",
            content="Please focus on auth",
            message_type="user_message",
        )

        messages = queue.get_all("test-sandbox")
        assert len(messages) == 1
        assert messages[0]["content"] == "Please focus on auth"
        assert messages[0]["message_type"] == "user_message"
        assert "timestamp" in messages[0]

    def test_queue_is_fifo(self):
        """UNIT: Messages should be retrieved in FIFO order."""
        from omoi_os.api.routes.sandbox import MessageQueue

        queue = MessageQueue()

        queue.enqueue("test", "First", "user_message")
        queue.enqueue("test", "Second", "user_message")
        queue.enqueue("test", "Third", "user_message")

        messages = queue.get_all("test")

        assert messages[0]["content"] == "First"
        assert messages[1]["content"] == "Second"
        assert messages[2]["content"] == "Third"

    def test_get_clears_queue(self):
        """UNIT: Getting messages should clear the queue."""
        from omoi_os.api.routes.sandbox import MessageQueue

        queue = MessageQueue()
        queue.enqueue("test", "Message", "user_message")

        first_get = queue.get_all("test")
        second_get = queue.get_all("test")

        assert len(first_get) == 1
        assert len(second_get) == 0

    def test_queues_are_isolated_by_sandbox_id(self):
        """UNIT: Different sandbox_ids should have separate queues."""
        from omoi_os.api.routes.sandbox import MessageQueue

        queue = MessageQueue()

        queue.enqueue("sandbox-a", "Message A", "user_message")
        queue.enqueue("sandbox-b", "Message B", "user_message")

        a_messages = queue.get_all("sandbox-a")
        b_messages = queue.get_all("sandbox-b")

        assert len(a_messages) == 1
        assert a_messages[0]["content"] == "Message A"
        assert len(b_messages) == 1
        assert b_messages[0]["content"] == "Message B"

    def test_empty_queue_returns_empty_list(self):
        """UNIT: Non-existent sandbox should return empty list, not error."""
        from omoi_os.api.routes.sandbox import MessageQueue

        queue = MessageQueue()
        messages = queue.get_all("nonexistent-sandbox")

        assert messages == []


@pytest.mark.unit
class TestMessageSchema:
    """Test message schema validation logic."""

    def test_valid_message_passes_validation(self, sample_message):
        """UNIT: Valid message should pass schema validation."""
        from omoi_os.api.routes.sandbox import SandboxMessage

        msg = SandboxMessage(**sample_message)

        assert msg.content == "Please focus on authentication first."
        assert msg.message_type == "user_message"

    def test_missing_content_fails(self):
        """UNIT: Missing content should raise ValidationError."""
        from omoi_os.api.routes.sandbox import SandboxMessage
        from pydantic import ValidationError

        with pytest.raises(ValidationError) as exc:
            SandboxMessage(message_type="user_message")

        assert "content" in str(exc.value)

    def test_invalid_message_type_fails(self):
        """UNIT: Invalid message_type should raise ValidationError."""
        from omoi_os.api.routes.sandbox import SandboxMessage
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            SandboxMessage(content="test", message_type="invalid_type")

    def test_allowed_message_types(self):
        """UNIT: All valid message types should be accepted."""
        from omoi_os.api.routes.sandbox import SandboxMessage

        valid_types = ["user_message", "interrupt", "guardian_nudge", "system"]

        for msg_type in valid_types:
            msg = SandboxMessage(content="test", message_type=msg_type)
            assert msg.message_type == msg_type


@pytest.mark.unit
class TestMessageBroadcastLogic:
    """Test event broadcasting when message is queued."""

    def test_enqueue_broadcasts_event(self):
        """UNIT: Enqueueing message should broadcast MESSAGE_QUEUED event."""
        from omoi_os.api.routes.sandbox import enqueue_message_with_broadcast
        from omoi_os.api.routes.sandbox import MessageQueue

        mock_bus = MagicMock()
        queue = MessageQueue()

        enqueue_message_with_broadcast(
            sandbox_id="test-123",
            content="Focus on API",
            message_type="guardian_nudge",
            queue=queue,
            event_bus=mock_bus,
        )

        mock_bus.publish.assert_called_once()
        call_args = mock_bus.publish.call_args[0][0]
        assert "MESSAGE_QUEUED" in call_args.event_type
        assert call_args.entity_id == "test-123"

    def test_interrupt_has_high_priority_marker(self):
        """UNIT: Interrupt messages should be marked high priority."""
        from omoi_os.api.routes.sandbox import _create_message_event

        event = _create_message_event(
            sandbox_id="test",
            content="STOP",
            message_type="interrupt",
        )

        assert event.payload.get("priority") == "high"

    def test_normal_message_has_normal_priority(self):
        """UNIT: Non-interrupt messages should have normal priority."""
        from omoi_os.api.routes.sandbox import _create_message_event

        event = _create_message_event(
            sandbox_id="test",
            content="Hello",
            message_type="user_message",
        )

        assert event.payload.get("priority") == "normal"
