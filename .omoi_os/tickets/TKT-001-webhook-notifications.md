# TKT-001: Implement Webhook Notifications

**Status**: backlog
**Priority**: HIGH
**Estimate**: L
**Phase**: PHASE_IMPLEMENTATION
**Requirements**: REQ-WEBHOOK-CONFIG-001, REQ-WEBHOOK-CONFIG-002, REQ-WEBHOOK-EVENT-001, REQ-WEBHOOK-EVENT-002, REQ-WEBHOOK-EVENT-003
**Design Reference**: designs/webhook-notifications.md

## Description

Implement webhook notifications for task lifecycle events (completed, failed, agent stuck). This enables internal monitoring systems to receive real-time updates. Webhooks can be configured at project-level with optional per-ticket overrides.

## Acceptance Criteria

- [ ] Project model has `webhook_url` field
- [ ] Ticket model has `webhook_url` field
- [ ] Database migration adds both fields
- [ ] WebhookDeliveryService delivers HTTP POST with retry logic
- [ ] WebhookNotificationService subscribes to events and delivers webhooks
- [ ] API endpoints support updating webhook URLs
- [ ] Events trigger webhooks within 5-10 seconds
- [ ] Failed deliveries are logged but don't block task completion

## Dependencies

- None (extends existing infrastructure)

## Tasks

- TSK-001: Add webhook_url to Project and Ticket models
- TSK-002: Create database migration
- TSK-003: Implement WebhookDeliveryService
- TSK-004: Implement WebhookNotificationService
- TSK-005: Update API routes for webhook configuration
- TSK-006: Add unit and integration tests
