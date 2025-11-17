"""Test event bus service: publish/subscribe, callback invocation, error handling."""

import json
import threading
import time
from unittest.mock import Mock, patch

import pytest

from omoi_os.models.events import (
    AgentCollaborationTopics,
    AgentMessageEvent,
    AgentHandoffRequestedEvent,
    CollaborationThreadStartedEvent,
)
from omoi_os.services.event_bus import EventBusService, SystemEvent


@pytest.fixture
def event_bus_service(redis_url: str):
    """Create an event bus service (uses fakeredis if available, otherwise real Redis)."""
    # Try to use fakeredis for testing
    try:
        import fakeredis
        # Create a fake Redis server
        fake_server = fakeredis.FakeStrictRedis(decode_responses=True)
        
        # Patch redis.from_url to return our fake server
        patcher = patch('omoi_os.services.event_bus.redis.from_url', return_value=fake_server)
        patcher.start()
        try:
            bus = EventBusService("redis://fake:6379")
            yield bus
        finally:
            patcher.stop()
    except ImportError:
        # Fall back to real Redis if fakeredis not available
        bus = EventBusService(redis_url)
        yield bus


def test_publish_event(event_bus_service: EventBusService):
    """Test publishing an event."""
    event = SystemEvent(
        event_type="TASK_ASSIGNED",
        entity_type="task",
        entity_id="task-123",
        payload={"agent_id": "agent-456"},
    )

    # Should not raise an error
    event_bus_service.publish(event)
    assert event_bus_service.redis_client is not None


def test_subscribe_and_receive_event(event_bus_service: EventBusService):
    """Test subscribing to events and receiving them."""
    received_events = []
    event_received = threading.Event()

    def callback(event: SystemEvent) -> None:
        received_events.append(event)
        event_received.set()

    # Subscribe to TASK_ASSIGNED events
    event_bus_service.subscribe("TASK_ASSIGNED", callback)

    # Start listening in a background thread
    listen_thread = threading.Thread(target=event_bus_service.listen, daemon=True)
    listen_thread.start()

    # Give thread time to start
    time.sleep(0.1)

    # Publish an event
    event = SystemEvent(
        event_type="TASK_ASSIGNED",
        entity_type="task",
        entity_id="task-123",
        payload={"agent_id": "agent-456"},
    )
    event_bus_service.publish(event)

    # Wait for callback (with timeout)
    event_received.wait(timeout=2.0)

    # Verify callback was called
    assert len(received_events) > 0
    received = received_events[0]
    assert received.event_type == "TASK_ASSIGNED"
    assert received.entity_id == "task-123"
    assert received.payload == {"agent_id": "agent-456"}


def test_event_serialization(event_bus_service: EventBusService):
    """Test that events are properly serialized/deserialized."""
    received_events = []
    event_received = threading.Event()

    def callback(event: SystemEvent) -> None:
        received_events.append(event)
        event_received.set()

    event_bus_service.subscribe("TEST_EVENT", callback)

    # Start listening in a background thread
    listen_thread = threading.Thread(target=event_bus_service.listen, daemon=True)
    listen_thread.start()
    time.sleep(0.1)

    # Publish event with complex payload
    complex_payload = {
        "nested": {"key": "value"},
        "list": [1, 2, 3],
        "number": 42,
    }

    event = SystemEvent(
        event_type="TEST_EVENT",
        entity_type="test",
        entity_id="test-1",
        payload=complex_payload,
    )

    event_bus_service.publish(event)
    event_received.wait(timeout=2.0)

    # Verify payload was correctly deserialized
    assert len(received_events) > 0
    received = received_events[0]
    assert received.payload == complex_payload
    assert received.payload["nested"]["key"] == "value"
    assert received.payload["list"] == [1, 2, 3]


def test_typed_publish_wraps_system_event(event_bus_service: EventBusService):
    """Typed publish helpers should wrap payloads into SystemEvent objects."""
    payload = AgentMessageEvent(
        message_id="msg-1",
        thread_id="thread-1",
        sender_agent_id="agent-a",
        target_agent_id="agent-b",
        message_type="text",
        body_preview="Need assistance",
        metadata={"urgency": "high"},
    )

    with patch.object(event_bus_service, "publish") as publish_mock:
        event_bus_service.publish_agent_message_sent(payload)

    publish_mock.assert_called_once()
    event = publish_mock.call_args[0][0]
    assert event.event_type == AgentCollaborationTopics.MESSAGE_SENT
    assert event.entity_type == "agent_message"
    assert event.entity_id == "msg-1"
    assert event.payload["thread_id"] == "thread-1"


def test_typed_handoff_publish(event_bus_service: EventBusService):
    """Handoff helper should publish correct event metadata."""
    payload = AgentHandoffRequestedEvent(
        handoff_id="handoff-1",
        thread_id="thread-3",
        requesting_agent_id="agent-a",
        target_agent_id="agent-b",
        status="pending",
        required_capabilities=["python"],
        reason="Need python expert",
        task_id="task-1",
    )

    with patch.object(event_bus_service, "publish") as publish_mock:
        event_bus_service.publish_agent_handoff_requested(payload)

    event = publish_mock.call_args[0][0]
    assert event.event_type == AgentCollaborationTopics.HANDOFF_REQUESTED
    assert event.payload["status"] == "pending"
    assert event.payload["required_capabilities"] == ["python"]


def test_typed_subscribe_wraps_payload(event_bus_service: EventBusService):
    """Typed subscribe should convert SystemEvent payloads into dataclasses."""
    callback = Mock()

    with patch.object(event_bus_service, "subscribe") as subscribe_mock:
        event_bus_service.subscribe_agent_messages(callback)

    args, _ = subscribe_mock.call_args
    assert args[0] == AgentCollaborationTopics.MESSAGE_SENT
    handler = args[1]

    system_event = SystemEvent(
        event_type=AgentCollaborationTopics.MESSAGE_SENT,
        entity_type="agent_message",
        entity_id="msg-2",
        payload={
            "message_id": "msg-2",
            "thread_id": "thread-1",
            "sender_agent_id": "agent-a",
            "target_agent_id": None,
            "message_type": "text",
            "body_preview": "hi",
            "metadata": None,
        },
    )

    handler(system_event)
    callback.assert_called_once()
    assert isinstance(callback.call_args[0][0], AgentMessageEvent)


def test_collab_started_publish(event_bus_service: EventBusService):
    """Collaboration start helper should publish expected topic."""
    payload = CollaborationThreadStartedEvent(
        thread_id="thread-xyz",
        subject="Review",
        context_type="ticket",
        context_id="ticket-1",
        created_by_agent_id="agent-a",
        participants=["agent-a", "agent-b"],
    )

    with patch.object(event_bus_service, "publish") as publish_mock:
        event_bus_service.publish_agent_collaboration_started(payload)

    event = publish_mock.call_args[0][0]
    assert event.event_type == AgentCollaborationTopics.COLLABORATION_STARTED
    assert event.payload["participants"] == ["agent-a", "agent-b"]

