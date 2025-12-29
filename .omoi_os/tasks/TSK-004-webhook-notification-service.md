---
id: TSK-004
title: Implement WebhookNotificationService
status: pending
parent_ticket: TKT-001
estimate: M
created: 2025-12-29
assignee: null
dependencies:
  depends_on:
    - TSK-002
    - TSK-003
  blocks:
    - TSK-006
---

# TSK-004: Implement WebhookNotificationService

## Objective

Create service that subscribes to EventBus events and delivers webhooks using WebhookDeliveryService.

---

## Deliverables

- [ ] `backend/omoi_os/services/webhook_notification.py`
- [ ] `backend/tests/integration/services/test_webhook_notification.py`

---

## Implementation Notes

### Approach

1. Create WebhookNotificationService class
2. Subscribe to events: `task.completed`, `task.failed`, `agent.stuck`
3. Implement URL resolution (ticket override → project fallback)
4. Build standardized payload
5. Deliver via WebhookDeliveryService
6. Write integration tests

### Code Patterns

URL resolution logic:
```python
async def _resolve_webhook_url(self, ticket_id: str) -> Optional[str]:
    ticket = session.get(Ticket, ticket_id)
    if ticket.webhook_url:
        return ticket.webhook_url
    if ticket.project and ticket.project.webhook_url:
        return ticket.project.webhook_url
    return None
```

Payload format:
```json
{
  "event_type": "task.completed",
  "timestamp": "ISO8601",
  "entity_type": "task",
  "entity_id": "...",
  "project_id": "...",
  "ticket_id": "...",
  "task_id": "...",
  "agent_id": "...",
  "data": { ... }
}
```

Event subscription:
```python
class WebhookNotificationService:
    def __init__(self, event_bus: EventBusService, delivery: WebhookDeliveryService):
        self.event_bus = event_bus
        self.delivery = delivery

    async def start(self):
        await self.event_bus.subscribe("task.completed", self._handle_event)
        await self.event_bus.subscribe("task.failed", self._handle_event)
        await self.event_bus.subscribe("agent.stuck", self._handle_event)
```

### References
- designs/webhook-notifications.md#notification-flow
- backend/omoi_os/services/event_bus.py

---

## Acceptance Criteria

- [ ] Subscribes to correct events on startup
- [ ] Resolves URL with correct precedence (ticket > project)
- [ ] Payload matches documented schema
- [ ] Delivery failures don't block event processing
- [ ] No webhook when URL is None (no error)

---

## Testing Requirements

### Integration Tests
```python
async def test_task_completed_triggers_webhook():
    # Setup: project with webhook_url
    # Action: emit task.completed event
    # Assert: webhook delivered with correct payload

async def test_ticket_url_overrides_project():
    # Setup: project with URL A, ticket with URL B
    # Action: emit event for that ticket's task
    # Assert: webhook delivered to URL B
```

### Edge Cases
- No webhook configured (should not error)
- Ticket without project
- Delivery failure (should log but not raise)

---

## Notes

Depends on TSK-003 (WebhookDeliveryService) for actual HTTP delivery.
