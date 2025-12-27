# TSK-004: Implement WebhookNotificationService

**Status**: pending
**Parent Ticket**: TKT-001
**Estimate**: M
**Assignee**: (unassigned)
**Depends On**: TSK-001, TSK-003

## Objective

Create service that subscribes to EventBus events and delivers webhooks.

## Deliverables

- [ ] `backend/omoi_os/services/webhook_notification.py`
- [ ] `backend/tests/integration/services/test_webhook_notification.py`

## Implementation Notes

1. Subscribe to events: `task.completed`, `task.failed`, `agent.stuck`
2. Resolve webhook URL (ticket override → project fallback)
3. Build standardized payload
4. Deliver via WebhookDeliveryService

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

## Acceptance Criteria

- Subscribes to correct events on startup
- Resolves URL with correct precedence (ticket > project)
- Payload matches documented schema
- Delivery failures don't block event processing
