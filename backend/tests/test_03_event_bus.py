"""Test event bus service: publish/subscribe, callback invocation, error handling."""

import threading
import time
from unittest.mock import patch

import pytest

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
        patcher = patch(
            "omoi_os.services.event_bus.redis.from_url", return_value=fake_server
        )
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
