# Webhook Notifications Requirements

**Feature**: webhook-notifications
**Created**: 2025-12-27
**Status**: Draft
**Author**: Claude (spec-driven-dev skill)

## Overview

Extend the existing AlertService/WebhookRouter to deliver webhook notifications for task lifecycle events. This enables internal monitoring systems to receive real-time updates when tasks complete, fail, or when agents become stuck.

## User Stories

1. As an **internal monitoring system**, I can receive webhook notifications when a task completes so that I can update dashboards and trigger downstream processes.

2. As an **internal monitoring system**, I can receive webhook notifications when a task fails so that I can alert operators and log the failure.

3. As an **internal monitoring system**, I can receive webhook notifications when an agent becomes stuck so that intervention can be triggered.

4. As a **project administrator**, I can configure a webhook URL at the project level so that all tickets in that project send notifications to the same endpoint.

5. As a **ticket creator**, I can override the webhook URL for a specific ticket so that its events go to a different endpoint than the project default.

## Requirements

### REQ-WEBHOOK-CONFIG-001: Project-Level Webhook Configuration

**WHEN** a project is created or updated,
**THE SYSTEM SHALL** allow storing a webhook URL that applies to all tickets in that project.

**Acceptance Criteria:**
- [ ] Project model includes `webhook_url` field (nullable string)
- [ ] API endpoint to update project webhook URL
- [ ] Webhook URL is validated as a valid HTTP/HTTPS URL

### REQ-WEBHOOK-CONFIG-002: Ticket-Level Webhook Override

**WHEN** a ticket is created or updated,
**THE SYSTEM SHALL** allow storing a webhook URL that overrides the project-level configuration.

**Acceptance Criteria:**
- [ ] Ticket model includes `webhook_url` field (nullable string)
- [ ] If ticket has webhook_url, use it; otherwise fall back to project webhook_url
- [ ] API endpoint to update ticket webhook URL

### REQ-WEBHOOK-EVENT-001: Task Completed Event

**WHEN** a task transitions to `completed` status,
**THE SYSTEM SHALL** deliver a webhook notification to the configured endpoint.

**Acceptance Criteria:**
- [ ] Webhook payload includes: event_type, task_id, ticket_id, project_id, timestamp, result summary
- [ ] Delivery occurs within 5 seconds of task completion
- [ ] Failed deliveries are logged but do not block task completion

### REQ-WEBHOOK-EVENT-002: Task Failed Event

**WHEN** a task transitions to `failed` status,
**THE SYSTEM SHALL** deliver a webhook notification to the configured endpoint.

**Acceptance Criteria:**
- [ ] Webhook payload includes: event_type, task_id, ticket_id, project_id, timestamp, error message, retry_count
- [ ] Delivery occurs within 5 seconds of task failure

### REQ-WEBHOOK-EVENT-003: Agent Stuck Event

**WHEN** an agent is detected as stuck (no heartbeat for >90 seconds or trajectory analysis indicates stuck state),
**THE SYSTEM SHALL** deliver a webhook notification to the configured endpoint.

**Acceptance Criteria:**
- [ ] Webhook payload includes: event_type, agent_id, task_id, ticket_id, project_id, timestamp, last_heartbeat, stuck_reason
- [ ] Delivery occurs within 10 seconds of stuck detection

### REQ-WEBHOOK-DELIVERY-001: Webhook Delivery Mechanism

**THE SYSTEM SHALL** deliver webhooks via HTTP POST with JSON payload.

**Acceptance Criteria:**
- [ ] Content-Type: application/json
- [ ] HTTP timeout: 10 seconds
- [ ] Retry on 5xx errors: 3 attempts with exponential backoff (1s, 2s, 4s)
- [ ] Log all delivery attempts (success and failure)

### REQ-WEBHOOK-PAYLOAD-001: Standard Payload Format

**THE SYSTEM SHALL** use a consistent payload format for all webhook events.

**Payload Schema:**
```json
{
  "event_type": "task.completed | task.failed | agent.stuck",
  "timestamp": "2025-12-27T12:00:00Z",
  "project_id": "proj-123",
  "ticket_id": "ticket-456",
  "task_id": "task-789",
  "agent_id": "agent-abc",
  "data": {
    // Event-specific data
  }
}
```

## Out of Scope

- User-configurable webhook endpoints (future feature)
- Rate limiting
- Payload signing (HMAC)
- Webhook delivery UI/history

## Dependencies

- Existing `AlertService` in `backend/omoi_os/services/alerting.py`
- Existing `EventBusService` for event subscription
- Existing `WebhookRouter` placeholder (to be implemented)

## References

- `backend/omoi_os/services/alerting.py` - Existing alert infrastructure
- `backend/omoi_os/services/event_bus.py` - Event publishing system
