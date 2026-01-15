"""Event bus service for system-wide event publishing and subscription."""

import json
import logging
from typing import Any, Callable, Dict, Optional

import redis
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SystemEvent(BaseModel):
    """System-wide orchestration event (not OpenHands conversation events)."""

    event_type: str = Field(..., description="Event type: TASK_ASSIGNED, TASK_COMPLETED, etc.")
    entity_type: str = Field(..., description="Entity type: ticket, task, agent")
    entity_id: str = Field(..., description="ID of the entity")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event payload data")


class EventBusService:
    """Manages system-wide event publishing and subscription via Redis Pub/Sub.

    If Redis is unavailable, operations are no-ops (graceful degradation).
    """

    def __init__(self, redis_url: str | None = None):
        """
        Initialize event bus service.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub = None
        self._available = False

        # If no URL provided, try to get from settings
        if redis_url is None:
            try:
                from omoi_os.config import get_app_settings
                redis_url = get_app_settings().redis.url
            except Exception:
                pass  # Will be handled below

        # Validate URL has a proper host (not just "redis://" or local-only)
        # Check for minimal valid URL pattern (redis://host or redis://host:port)
        from urllib.parse import urlparse
        parsed = urlparse(redis_url) if redis_url else None

        if not parsed or not parsed.hostname:
            logger.warning("Redis URL not configured or invalid, EventBus will be disabled")
            return

        try:
            # Add socket timeout to prevent blocking forever on unreachable hosts
            self.redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
            )
            # Test connection with timeout
            self.redis_client.ping()
            self.pubsub = self.redis_client.pubsub()
            self._available = True
            logger.info("EventBus connected to Redis")
        except redis.exceptions.ConnectionError as e:
            logger.warning(f"Redis connection failed, EventBus disabled: {e}")
        except redis.exceptions.TimeoutError as e:
            logger.warning(f"Redis connection timed out, EventBus disabled: {e}")
        except Exception as e:
            logger.warning(f"Redis initialization failed, EventBus disabled: {e}")

    def publish(self, event: SystemEvent) -> None:
        """
        Publish event to system bus.

        Args:
            event: SystemEvent to publish
        """
        if not self._available or not self.redis_client:
            return  # Graceful no-op when Redis unavailable

        channel = f"events.{event.event_type}"
        # Use Pydantic's model_dump_json for automatic JSON serialization
        # This handles UUID and other types automatically
        message = event.model_dump_json()
        try:
            self.redis_client.publish(channel, message)
        except redis.exceptions.ConnectionError:
            logger.warning("Redis connection lost during publish")

    def subscribe(self, event_type: str, callback: Callable[[SystemEvent], None]) -> None:
        """
        Subscribe to event type.

        Args:
            event_type: Event type to subscribe to (e.g., "TASK_ASSIGNED")
            callback: Function to call when event is received
                     Signature: callback(event: SystemEvent) -> None
        """
        if not self._available or not self.pubsub:
            return  # Graceful no-op when Redis unavailable

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
        if not self._available or not self.pubsub:
            return  # Graceful no-op when Redis unavailable

        for message in self.pubsub.listen():
            # Callbacks are invoked automatically via subscribe()
            pass

    def close(self) -> None:
        """Close Redis connections."""
        if self.pubsub:
            self.pubsub.close()
        if self.redis_client:
            self.redis_client.close()
