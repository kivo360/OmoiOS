"""WebSocket API routes for real-time event streaming."""

import asyncio
import json
from typing import List, Optional, Set

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from omoi_os.logging import get_logger
from omoi_os.services.event_bus import EventBusService, SystemEvent

logger = get_logger(__name__)

router = APIRouter()


class EventSubscriptionRequest(BaseModel):
    """Request model for subscribing to specific event types."""

    event_types: Optional[List[str]] = None
    entity_types: Optional[List[str]] = None
    entity_ids: Optional[List[str]] = None


class WebSocketEventManager:
    """Manages WebSocket connections and event subscriptions."""

    def __init__(self, event_bus: EventBusService):
        self.event_bus = event_bus
        self.active_connections: Set[WebSocket] = set()
        self.connection_filters: dict[WebSocket, dict] = {}
        self.redis_listener_task: Optional[asyncio.Task] = None
        self.redis_pubsub = None

    async def connect(self, websocket: WebSocket, filters: Optional[dict] = None):
        """Accept WebSocket connection and store filters."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.connection_filters[websocket] = filters or {}

        if not self.redis_listener_task or self.redis_listener_task.done():
            self._start_redis_listener()

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        self.active_connections.discard(websocket)
        self.connection_filters.pop(websocket, None)

    def _start_redis_listener(self):
        """Start background task to listen to Redis Pub/Sub."""
        self.redis_pubsub = self.event_bus.redis_client.pubsub()
        self.redis_listener_task = asyncio.create_task(self._listen_to_redis())

    async def _listen_to_redis(self):
        """Listen to Redis Pub/Sub and forward events to WebSocket clients."""
        # Subscribe to all event channels (pattern: events.*)
        loop = asyncio.get_event_loop()

        def subscribe():
            self.redis_pubsub.psubscribe("events.*")

        await loop.run_in_executor(None, subscribe)

        try:
            while True:
                # Run blocking Redis get_message in executor
                message = await loop.run_in_executor(
                    None,
                    lambda: self.redis_pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    ),
                )

                if message is None:
                    continue

                if message["type"] == "pmessage":
                    data = json.loads(message["data"])

                    event = SystemEvent(
                        event_type=data["event_type"],
                        entity_type=data["entity_type"],
                        entity_id=data["entity_id"],
                        payload=data["payload"],
                    )

                    # Forward to all connected clients that match filters
                    await self._broadcast_event(event)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("Error in Redis listener", error=str(e), exc_info=True)
        finally:
            if self.redis_pubsub:

                def close():
                    self.redis_pubsub.close()

                await loop.run_in_executor(None, close)

    async def _broadcast_event(self, event: SystemEvent):
        """Broadcast event to all matching WebSocket connections."""
        disconnected = set()

        for websocket in self.active_connections:
            try:
                filters = self.connection_filters.get(websocket, {})

                # Apply filters
                if not self._matches_filters(event, filters):
                    continue

                # Send event to client
                await websocket.send_json(
                    {
                        "event_type": event.event_type,
                        "entity_type": event.entity_type,
                        "entity_id": event.entity_id,
                        "payload": event.payload,
                    }
                )
            except Exception as e:
                logger.error("Error sending event to WebSocket client", error=str(e))
                disconnected.add(websocket)

        # Clean up disconnected clients
        for ws in disconnected:
            self.disconnect(ws)

    def _matches_filters(self, event: SystemEvent, filters: dict) -> bool:
        """Check if event matches connection filters."""
        event_types = filters.get("event_types")
        if event_types and event.event_type not in event_types:
            return False

        entity_types = filters.get("entity_types")
        if entity_types and event.entity_type not in entity_types:
            return False

        entity_ids = filters.get("entity_ids")
        if entity_ids and event.entity_id not in entity_ids:
            return False

        return True

    async def close_all(self):
        """Close all connections and cleanup."""
        if self.redis_listener_task:
            self.redis_listener_task.cancel()
            try:
                await self.redis_listener_task
            except asyncio.CancelledError:
                pass

        for websocket in list(self.active_connections):
            try:
                await websocket.close()
            except Exception:
                pass

        self.active_connections.clear()
        self.connection_filters.clear()


# Global WebSocket manager instance
_ws_manager: Optional[WebSocketEventManager] = None


def get_ws_manager() -> WebSocketEventManager:
    """Get or create WebSocket event manager singleton."""
    global _ws_manager
    if _ws_manager is None:
        from omoi_os.api.dependencies import get_event_bus_service

        event_bus = get_event_bus_service()
        _ws_manager = WebSocketEventManager(event_bus)
    return _ws_manager


@router.websocket("/ws/events")
async def websocket_events(
    websocket: WebSocket,
    event_types: Optional[str] = Query(
        None, description="Comma-separated list of event types to filter"
    ),
    entity_types: Optional[str] = Query(
        None, description="Comma-separated list of entity types to filter"
    ),
    entity_ids: Optional[str] = Query(
        None, description="Comma-separated list of entity IDs to filter"
    ),
):
    """
    WebSocket endpoint for real-time event streaming.

    Clients can filter events by:
    - event_types: Comma-separated list (e.g., "TASK_ASSIGNED,TASK_COMPLETED")
    - entity_types: Comma-separated list (e.g., "task,ticket")
    - entity_ids: Comma-separated list of specific entity IDs

    Events are streamed as JSON messages with the format:
    {
        "event_type": "TASK_ASSIGNED",
        "entity_type": "task",
        "entity_id": "uuid",
        "payload": {...}
    }
    """
    # Handle case where services aren't ready yet
    try:
        ws_manager = get_ws_manager()
    except RuntimeError:
        await websocket.accept()
        await websocket.send_json({"error": "Service not ready, please retry"})
        await websocket.close(code=1013)  # Try again later
        return

    # Parse query parameter filters
    filters = {}
    if event_types:
        filters["event_types"] = [et.strip() for et in event_types.split(",")]
    if entity_types:
        filters["entity_types"] = [et.strip() for et in entity_types.split(",")]
    if entity_ids:
        filters["entity_ids"] = [ei.strip() for ei in entity_ids.split(",")]

    await ws_manager.connect(websocket, filters)

    try:
        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (can be used for dynamic filter updates)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                try:
                    message = json.loads(data)
                    if message.get("type") == "subscribe":
                        # Update filters dynamically
                        new_filters = {}
                        if "event_types" in message:
                            new_filters["event_types"] = message["event_types"]
                        if "entity_types" in message:
                            new_filters["entity_types"] = message["entity_types"]
                        if "entity_ids" in message:
                            new_filters["entity_ids"] = message["entity_ids"]

                        ws_manager.connection_filters[websocket].update(new_filters)
                        await websocket.send_json(
                            {"status": "subscribed", "filters": new_filters}
                        )
                except json.JSONDecodeError:
                    await websocket.send_json({"error": "Invalid JSON message"})
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket)
