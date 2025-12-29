---
id: TKT-001
title: Implement Webhook Notifications
status: backlog
priority: HIGH
estimate: L
created: 2025-12-29
updated: 2025-12-29
feature: webhook-notifications
requirements:
  - REQ-WEBHOOK-CONFIG-001
  - REQ-WEBHOOK-CONFIG-002
  - REQ-WEBHOOK-EVENT-001
  - REQ-WEBHOOK-EVENT-002
  - REQ-WEBHOOK-EVENT-003
design_ref: designs/webhook-notifications.md
tasks:
  - TSK-001
  - TSK-002
  - TSK-003
  - TSK-004
  - TSK-005
  - TSK-006
dependencies:
  blocked_by: []
  blocks: []
  related: []
---

# TKT-001: Implement Webhook Notifications

## Description

Implement webhook notifications for task lifecycle events (completed, failed, agent stuck). This enables internal monitoring systems to receive real-time updates. Webhooks can be configured at project-level with optional per-ticket overrides.

### Context
Internal monitoring systems need to receive real-time notifications when tasks complete, fail, or when agents get stuck. This allows dashboards and alerting systems to respond quickly to workflow events.

### Goals
- Enable webhook configuration at project and ticket levels
- Deliver notifications for key lifecycle events
- Provide reliable delivery with retry logic

### Non-Goals
- External third-party integrations (Slack, Discord, etc.) - future enhancement
- Webhook authentication/signing - future enhancement

---

## Acceptance Criteria

- [ ] Project model has `webhook_url` field
- [ ] Ticket model has `webhook_url` field
- [ ] Database migration adds both fields
- [ ] WebhookDeliveryService delivers HTTP POST with retry logic
- [ ] WebhookNotificationService subscribes to events and delivers webhooks
- [ ] API endpoints support updating webhook URLs
- [ ] Events trigger webhooks within 5-10 seconds
- [ ] Failed deliveries are logged but don't block task completion

---

## Technical Notes

### Implementation Approach
1. Add model fields (TSK-001)
2. Create migration (TSK-002)
3. Implement delivery service (TSK-003)
4. Implement notification service (TSK-004)
5. Update API routes (TSK-005)
6. Add tests (TSK-006)

### Key Files
- `backend/omoi_os/models/project.py` - Add webhook_url field
- `backend/omoi_os/models/ticket.py` - Add webhook_url field
- `backend/omoi_os/services/webhook_delivery.py` - HTTP delivery with retries
- `backend/omoi_os/services/webhook_notification.py` - Event subscription and dispatch

### API Changes
- PATCH /api/v1/projects/{id} - accepts webhook_url
- PATCH /api/v1/tickets/{id} - accepts webhook_url

### Database Changes
- projects.webhook_url (VARCHAR 2048, nullable)
- tickets.webhook_url (VARCHAR 2048, nullable)

---

## Testing Strategy

### Unit Tests
- WebhookDeliveryService retry logic
- URL resolution precedence

### Integration Tests
- Event triggers webhook delivery
- API endpoints accept webhook URLs

### Manual Testing
- Configure webhook URL and trigger a task completion
- Verify webhook payload matches schema

---

## Rollback Plan

1. Run `alembic downgrade -1` to remove columns
2. Revert code changes via git

---

## Notes

This extends existing EventBusService infrastructure. No external dependencies required.
