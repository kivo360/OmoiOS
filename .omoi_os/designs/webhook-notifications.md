# Webhook Notifications Design

**Feature**: webhook-notifications
**Created**: 2025-12-27
**Status**: Draft
**Requirements**: REQ-WEBHOOK-CONFIG-001, REQ-WEBHOOK-CONFIG-002, REQ-WEBHOOK-EVENT-001, REQ-WEBHOOK-EVENT-002, REQ-WEBHOOK-EVENT-003

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Event Sources                                  │
├─────────────────┬─────────────────┬─────────────────────────────────────┤
│  TaskQueue      │  Guardian       │  AgentHealthService                 │
│  (task.*)       │  (agent.stuck)  │  (heartbeat timeout)                │
└────────┬────────┴────────┬────────┴────────────────┬────────────────────┘
         │                 │                          │
         ▼                 ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        EventBusService                                   │
│         subscribe("task.*", "agent.stuck", "agent.health.*")            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     WebhookNotificationService                           │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  │
│  │ Event Handler   │─>│ URL Resolver     │─>│ WebhookDeliveryService │  │
│  │ (filter events) │  │ (ticket→project) │  │ (HTTP POST + retry)    │  │
│  └─────────────────┘  └──────────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                          External Webhook Endpoints
```

## Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| `WebhookNotificationService` | Orchestrates event→webhook flow, subscribes to EventBus |
| `WebhookURLResolver` | Resolves webhook URL from ticket or project |
| `WebhookDeliveryService` | HTTP delivery with retry logic, logging |
| `WebhookPayloadBuilder` | Constructs standardized JSON payloads |

## Data Model Changes

### Project Model Addition

```python
# In backend/omoi_os/models/project.py

class Project(Base):
    # ... existing fields ...

    # NEW: Webhook configuration
    webhook_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
        comment="Webhook URL for project-level notifications"
    )
```

### Ticket Model Addition

```python
# In backend/omoi_os/models/ticket.py

class Ticket(Base):
    # ... existing fields ...

    # NEW: Webhook override
    webhook_url: Mapped[Optional[str]] = mapped_column(
        String(2048),
        nullable=True,
        comment="Webhook URL override (takes precedence over project webhook)"
    )
```

### Migration

```python
# migrations/versions/xxx_add_webhook_url_fields.py

def upgrade():
    op.add_column('projects', sa.Column('webhook_url', sa.String(2048), nullable=True))
    op.add_column('tickets', sa.Column('webhook_url', sa.String(2048), nullable=True))

def downgrade():
    op.drop_column('tickets', 'webhook_url')
    op.drop_column('projects', 'webhook_url')
```

## Service Implementation

### WebhookNotificationService

```python
# backend/omoi_os/services/webhook_notification.py

from typing import Optional
import httpx
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.database import DatabaseService
from omoi_os.logging import get_logger

logger = get_logger(__name__)

class WebhookNotificationService:
    """Delivers webhook notifications for task lifecycle events."""

    # Events we care about
    SUBSCRIBED_EVENTS = [
        "task.completed",
        "task.failed",
        "agent.stuck",
    ]

    def __init__(
        self,
        db: DatabaseService,
        event_bus: EventBusService,
    ):
        self.db = db
        self.event_bus = event_bus
        self.delivery = WebhookDeliveryService()
        self._subscribe_to_events()

    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events on EventBus."""
        for event_type in self.SUBSCRIBED_EVENTS:
            self.event_bus.subscribe(event_type, self._handle_event)

    async def _handle_event(self, event: SystemEvent) -> None:
        """Handle incoming event and deliver webhook if configured."""
        # Extract task/ticket/project from event
        task_id = event.payload.get("task_id")
        ticket_id = event.payload.get("ticket_id") or event.entity_id

        # Resolve webhook URL
        webhook_url = await self._resolve_webhook_url(ticket_id)
        if not webhook_url:
            logger.debug(f"No webhook configured for ticket {ticket_id}")
            return

        # Build payload
        payload = self._build_payload(event)

        # Deliver
        await self.delivery.deliver(webhook_url, payload)

    async def _resolve_webhook_url(self, ticket_id: str) -> Optional[str]:
        """Resolve webhook URL from ticket or project."""
        with self.db.get_session() as session:
            from omoi_os.models.ticket import Ticket

            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return None

            # Ticket-level override takes precedence
            if ticket.webhook_url:
                return ticket.webhook_url

            # Fall back to project-level
            if ticket.project and ticket.project.webhook_url:
                return ticket.project.webhook_url

            return None

    def _build_payload(self, event: SystemEvent) -> dict:
        """Build standardized webhook payload."""
        return {
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "project_id": event.payload.get("project_id"),
            "ticket_id": event.payload.get("ticket_id"),
            "task_id": event.payload.get("task_id"),
            "agent_id": event.payload.get("agent_id"),
            "data": event.payload,
        }
```

### WebhookDeliveryService

```python
# backend/omoi_os/services/webhook_delivery.py

import asyncio
from typing import Any
import httpx
from omoi_os.logging import get_logger

logger = get_logger(__name__)

class WebhookDeliveryService:
    """HTTP webhook delivery with retry logic."""

    TIMEOUT_SECONDS = 10.0
    MAX_RETRIES = 3
    RETRY_DELAYS = [1.0, 2.0, 4.0]  # Exponential backoff

    async def deliver(self, url: str, payload: dict[str, Any]) -> bool:
        """
        Deliver webhook with retries.

        Returns True if delivery succeeded, False otherwise.
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS) as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )

                    if response.status_code < 400:
                        logger.info(
                            f"Webhook delivered successfully",
                            extra={
                                "url": url,
                                "status": response.status_code,
                                "event_type": payload.get("event_type"),
                            }
                        )
                        return True

                    if response.status_code >= 500:
                        # Server error - retry
                        logger.warning(
                            f"Webhook delivery got 5xx, will retry",
                            extra={
                                "url": url,
                                "status": response.status_code,
                                "attempt": attempt + 1,
                            }
                        )
                    else:
                        # Client error (4xx) - don't retry
                        logger.error(
                            f"Webhook delivery got 4xx, not retrying",
                            extra={
                                "url": url,
                                "status": response.status_code,
                                "response": response.text[:500],
                            }
                        )
                        return False

            except httpx.TimeoutException:
                logger.warning(
                    f"Webhook delivery timeout",
                    extra={"url": url, "attempt": attempt + 1}
                )
            except Exception as e:
                logger.error(
                    f"Webhook delivery error: {e}",
                    extra={"url": url, "attempt": attempt + 1}
                )

            # Wait before retry (if not last attempt)
            if attempt < self.MAX_RETRIES - 1:
                await asyncio.sleep(self.RETRY_DELAYS[attempt])

        logger.error(
            f"Webhook delivery failed after {self.MAX_RETRIES} attempts",
            extra={"url": url, "event_type": payload.get("event_type")}
        )
        return False
```

## API Endpoints

### Update Project Webhook

```
PATCH /api/v1/projects/{project_id}
Content-Type: application/json

{
  "webhook_url": "https://internal.example.com/hooks/omoios"
}
```

### Update Ticket Webhook

```
PATCH /api/v1/tickets/{ticket_id}
Content-Type: application/json

{
  "webhook_url": "https://internal.example.com/hooks/specific-ticket"
}
```

## Event Payload Examples

### task.completed

```json
{
  "event_type": "task.completed",
  "timestamp": "2025-12-27T14:30:00Z",
  "entity_type": "task",
  "entity_id": "task-abc123",
  "project_id": "project-xyz",
  "ticket_id": "ticket-456",
  "task_id": "task-abc123",
  "agent_id": "agent-789",
  "data": {
    "result": "success",
    "duration_seconds": 45,
    "output_summary": "Implemented feature X"
  }
}
```

### task.failed

```json
{
  "event_type": "task.failed",
  "timestamp": "2025-12-27T14:35:00Z",
  "entity_type": "task",
  "entity_id": "task-def456",
  "project_id": "project-xyz",
  "ticket_id": "ticket-456",
  "task_id": "task-def456",
  "agent_id": "agent-789",
  "data": {
    "error": "Build failed: missing dependency",
    "retry_count": 2,
    "max_retries": 3
  }
}
```

### agent.stuck

```json
{
  "event_type": "agent.stuck",
  "timestamp": "2025-12-27T14:40:00Z",
  "entity_type": "agent",
  "entity_id": "agent-789",
  "project_id": "project-xyz",
  "ticket_id": "ticket-456",
  "task_id": "task-ghi789",
  "agent_id": "agent-789",
  "data": {
    "last_heartbeat": "2025-12-27T14:38:00Z",
    "stuck_reason": "no_heartbeat",
    "seconds_since_heartbeat": 120
  }
}
```

## Integration Points

### Existing AlertService

The existing `WebhookRouter` in `alerting.py` (lines 349-355) is a placeholder. We will:
1. Replace the placeholder with actual implementation
2. Or create a separate `WebhookDeliveryService` that both can use

**Recommendation**: Create `WebhookDeliveryService` as a shared utility, then both `AlertService` and `WebhookNotificationService` can use it.

### EventBus Events to Emit

Ensure these events are published by the relevant services:

| Event | Source Service | Required Payload |
|-------|----------------|------------------|
| `task.completed` | `TaskQueueService` | task_id, ticket_id, project_id, result |
| `task.failed` | `TaskQueueService` | task_id, ticket_id, project_id, error, retry_count |
| `agent.stuck` | `IntelligentGuardian` or `AgentHealthService` | agent_id, task_id, ticket_id, last_heartbeat |

## Testing Strategy

1. **Unit Tests**: WebhookDeliveryService retry logic, payload building
2. **Integration Tests**: Full flow from event → webhook delivery (mock HTTP)
3. **Manual Testing**: Configure webhook URL, trigger events, verify delivery

## File Changes Summary

| File | Change |
|------|--------|
| `models/project.py` | Add `webhook_url` field |
| `models/ticket.py` | Add `webhook_url` field |
| `migrations/versions/xxx_add_webhook_url.py` | New migration |
| `services/webhook_notification.py` | New service |
| `services/webhook_delivery.py` | New shared delivery service |
| `api/routes/projects.py` | Update to handle webhook_url |
| `api/routes/tickets.py` | Update to handle webhook_url |
| `services/__init__.py` | Export new services |
