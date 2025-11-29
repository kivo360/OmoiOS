"""Event bus service for system-wide event publishing and subscription."""

import json
from typing import Any, Callable, Dict

import redis
from pydantic import BaseModel, Field


class SystemEvent(BaseModel):
    """System-wide orchestration event (not OpenHands conversation events)."""

    event_type: str = Field(..., description="Event type: TASK_ASSIGNED, TASK_COMPLETED, etc.")
    entity_type: str = Field(..., description="Entity type: ticket, task, agent")
    entity_id: str = Field(..., description="ID of the entity")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")


class EventBusService:
    """Manages system-wide event publishing and subscription via Redis Pub/Sub."""

    def __init__(self, redis_url: str = "redis://localhost:16379"):
        """
        Initialize event bus service.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis_client.pubsub()

    def publish(self, event: SystemEvent) -> None:
        """
        Publish event to system bus.

        Args:
            event: SystemEvent to publish
        """
        channel = f"events.{event.event_type}"
        # Use Pydantic's model_dump_json for automatic JSON serialization
        # This handles UUID and other types automatically
        message = event.model_dump_json()
        self.redis_client.publish(channel, message)

    def subscribe(self, event_type: str, callback: Callable[[SystemEvent], None]) -> None:
        """
        Subscribe to event type.

        Args:
            event_type: Event type to subscribe to (e.g., "TASK_ASSIGNED")
            callback: Function to call when event is received
                     Signature: callback(event: SystemEvent) -> None
        """
        channel = f"events.{event_type}"

        def message_handler(message: dict) -> None:
            if message["type"] == "message":
                data = json.loads(message["data"])
                event = SystemEvent(
                    event_type=data["event_type"],
                    entity_type=data["entity_type"],
                    entity_id=data["entity_id"],
                    payload=data["payload"],
                )
                callback(event)

        self.pubsub.subscribe(**{channel: message_handler})

    def listen(self) -> None:
        """
        Start listening for events (blocking).

        Callbacks registered via subscribe() will be invoked automatically.
        """
        for message in self.pubsub.listen():
            # Callbacks are invoked automatically via subscribe()
            pass

    def close(self) -> None:
        """Close Redis connections."""
        self.pubsub.close()
        self.redis_client.close()
