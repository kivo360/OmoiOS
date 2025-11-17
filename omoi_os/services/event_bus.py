"""Event bus service for system-wide event publishing and subscription."""

import json
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict

import redis

from omoi_os.models.event import (
    AgentCollaborationTopics,
    AgentHandoffRequestedEvent,
    AgentMessageEvent,
    CollaborationThreadStartedEvent,
)


@dataclass
class SystemEvent:
    """System-wide orchestration event (not OpenHands conversation events)."""

    event_type: str  # TASK_ASSIGNED, TASK_COMPLETED, AGENT_REGISTERED, etc.
    entity_type: str  # ticket, task, agent
    entity_id: str
    payload: Dict[str, Any]


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
        message = json.dumps(
            {
                "event_type": event.event_type,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "payload": event.payload,
            }
        )
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

    # ------------------------------------------------------------------
    # Typed collaboration helpers
    # ------------------------------------------------------------------

    def publish_agent_message_sent(self, event: AgentMessageEvent) -> None:
        """Publish agent.message.sent."""
        self.publish(
            SystemEvent(
                event_type=AgentCollaborationTopics.MESSAGE_SENT,
                entity_type="agent_message",
                entity_id=event.message_id,
                payload=asdict(event),
            )
        )

    def publish_agent_handoff_requested(self, event: AgentHandoffRequestedEvent) -> None:
        """Publish agent.handoff.requested."""
        self.publish(
            SystemEvent(
                event_type=AgentCollaborationTopics.HANDOFF_REQUESTED,
                entity_type="agent_handoff",
                entity_id=event.handoff_id,
                payload=asdict(event),
            )
        )

    def publish_agent_collaboration_started(self, event: CollaborationThreadStartedEvent) -> None:
        """Publish agent.collab.started."""
        self.publish(
            SystemEvent(
                event_type=AgentCollaborationTopics.COLLABORATION_STARTED,
                entity_type="agent_thread",
                entity_id=event.thread_id,
                payload=asdict(event),
            )
        )

    def subscribe_agent_messages(self, callback: Callable[[AgentMessageEvent], None]) -> None:
        """Subscribe to agent.message.sent events with typed payloads."""

        def handler(event: SystemEvent) -> None:
            callback(AgentMessageEvent(**event.payload))

        self.subscribe(AgentCollaborationTopics.MESSAGE_SENT, handler)

    def subscribe_agent_handoffs(
        self, callback: Callable[[AgentHandoffRequestedEvent], None]
    ) -> None:
        """Subscribe to handoff requested events."""

        def handler(event: SystemEvent) -> None:
            callback(AgentHandoffRequestedEvent(**event.payload))

        self.subscribe(AgentCollaborationTopics.HANDOFF_REQUESTED, handler)

    def subscribe_agent_collaboration_started(
        self, callback: Callable[[CollaborationThreadStartedEvent], None]
    ) -> None:
        """Subscribe to new collaboration thread events."""

        def handler(event: SystemEvent) -> None:
            callback(CollaborationThreadStartedEvent(**event.payload))

        self.subscribe(AgentCollaborationTopics.COLLABORATION_STARTED, handler)

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
