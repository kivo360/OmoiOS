---
id: REQ-NOTIF-001
title: Notification System Requirements
feature: notification-system
created: 2026-01-08
updated: 2026-01-08
status: draft
category: functional
priority: HIGH
prd_ref: docs/prd-notification-system.md
design_ref: designs/notification-system.md
---

# Notification System Requirements

## Overview

These requirements define the behavior of the User Notification System for OmoiOS. The system provides real-time and persistent notifications for user-specific events with configurable preferences and delivery tracking.

## Functional Requirements

### REQ-NOTIF-FUNC-001: Notification Creation

**Priority**: HIGH
**Category**: Functional

WHEN a notification-triggering event occurs, THE SYSTEM SHALL create a notification record in the database within 500ms.

**Acceptance Criteria**:
- [ ] Notification record includes: id, user_id, type, title, message, data, status, created_at
- [ ] Notification status is initially "unread"
- [ ] Notification data includes relevant entity IDs (ticket_id, task_id, etc.)
- [ ] System logs notification creation for audit trail

**Notes**: Triggering events include: ticket_assigned, ticket_updated, task_completed, task_failed, approval_requested, agent_status_changed, system_alert

---

### REQ-NOTIF-FUNC-002: Real-Time WebSocket Delivery

**Priority**: HIGH
**Category**: Functional

WHEN a notification is created for a user with an active WebSocket connection, THE SYSTEM SHALL deliver the notification via WebSocket within 5 seconds.

**Acceptance Criteria**:
- [ ] WebSocket message includes notification object with all fields
- [ ] Message type is "notification_new"
- [ ] Delivery is attempted for each active connection for the user
- [ ] Failed WebSocket deliveries don't prevent notification storage
- [ ] System logs WebSocket delivery success/failure

**Notes**: Integrates with existing `/api/v1/ws/events` endpoint

---

### REQ-NOTIF-FUNC-003: Notification Retrieval

**Priority**: HIGH
**Category**: Functional

WHEN a user requests their notifications, THE SYSTEM SHALL return paginated notifications filtered by read status and type.

**Acceptance Criteria**:
- [ ] API endpoint: GET /api/v1/notifications
- [ ] Query parameters: user_id (from auth), status (all|read|unread), type (optional), limit (default 50, max 100), offset
- [ ] Returns notifications ordered by created_at DESC
- [ ] Includes count of unread notifications in response headers
- [ ] Response includes: id, type, title, message, data, status, created_at

---

### REQ-NOTIF-FUNC-004: Mark as Read

**Priority**: HIGH
**Category**: Functional

WHEN a user marks a notification as read, THE SYSTEM SHALL update the notification status and decrement their unread count.

**Acceptance Criteria**:
- [ ] API endpoint: PATCH /api/v1/notifications/{id}/read
- [ ] Updates status to "read"
- [ ] Sets read_at timestamp
- [ ] User can only mark their own notifications
- [ ] Returns 404 if notification doesn't exist or doesn't belong to user
- [ ] WebSocket broadcasts "notification_read" event to user's sessions

---

### REQ-NOTIF-FUNC-005: Mark All as Read

**Priority**: MEDIUM
**Category**: Functional

WHEN a user marks all notifications as read, THE SYSTEM SHALL update all unread notifications in a single transaction.

**Acceptance Criteria**:
- [ ] API endpoint: POST /api/v1/notifications/read-all
- [ ] Updates all unread notifications for authenticated user
- [ ] Sets read_at timestamp on all affected notifications
- [ ] Returns count of notifications marked as read
- [ ] WebSocket broadcasts "notification_read_all" event

---

### REQ-NOTIF-FUNC-006: Notification Aggregation

**Priority**: MEDIUM
**Category**: Functional

WHEN multiple similar notifications are created within a 5-minute window, THE SYSTEM SHALL aggregate them into a single notification.

**Acceptance Criteria**:
- [ ] Aggregates notifications by type and grouping key (e.g., ticket_assigner_id)
- [ ] Aggregated notification title indicates count (e.g., "5 tickets assigned to you")
- [ ] Aggregated notification data includes array of original notification data
- [ ] Original individual notifications are stored but not displayed individually
- [ ] Aggregation window is configurable per notification type

**Notes**: Example: 5 tickets assigned by same user within 5 minutes → "John Doe assigned 5 tickets to you"

---

### REQ-NOTIF-FUNC-007: User Notification Preferences

**Priority**: HIGH
**Category**: Functional

WHEN a user updates their notification preferences, THE SYSTEM SHALL persist the changes and apply them to future notifications.

**Acceptance Criteria**:
- [ ] API endpoint: GET/PUT /api/v1/notifications/preferences
- [ ] Preferences include: enabled notification types, channels (in_app, email)
- [ ] Preferences are per-user
- [ ] System validates preference updates against allowed types
- [ ] Default preferences provided for new users
- [ ] Notifications not enabled in preferences are not created

---

### REQ-NOTIF-FUNC-008: Email Delivery (Optional)

**Priority**: MEDIUM
**Category**: Functional

WHEN a notification is created and the user has email enabled for that type, THE SYSTEM SHALL send an email within 30 seconds.

**Acceptance Criteria**:
- [ ] Email includes notification title, message, and link to relevant entity
- [ ] Email uses consistent branding template
- [ ] Email delivery failures are logged and retried up to 3 times
- [ ] Unsubscribe link included in emails
- [ ] Respects user's email preference per notification type

**Notes**: Implementation depends on email service selection

---

### REQ-NOTIF-FUNC-009: Rate Limiting

**Priority**: MEDIUM
**Category**: Functional

WHEN more than 10 notifications are created for a user within 1 hour, THE SYSTEM SHALL rate-limit additional notifications.

**Acceptance Criteria**:
- [ ] Rate limit is per-user
- [ ] Rate-limited notifications are stored but not delivered via WebSocket
- [ ] Rate-limited notifications appear in notification center
- [ ] User is notified when rate limiting activates
- [ ] Admin users are exempt from rate limiting
- [ ] Rate limit is configurable

---

### REQ-NOTIF-FUNC-010: Notification Cleanup

**Priority**: LOW
**Category**: Functional

WHEN a user has more than 1000 notifications, THE SYSTEM SHALL automatically delete the oldest read notifications.

**Acceptance Criteria**:
- [ ] Cleanup job runs daily
- [ ] Deletes oldest read notifications first
- [ ] Always keeps minimum of 100 most recent notifications
- [ ] Never deletes unread notifications
- [ ] Logs deleted notification count

---

### REQ-NOTIF-FUNC-011: Organization-Level Preferences

**Priority**: MEDIUM
**Category**: Functional

WHEN an organization admin sets default notification preferences, THE SYSTEM SHALL apply those defaults to new organization members.

**Acceptance Criteria**:
- [ ] Organization preferences stored separately from user preferences
- [ ] User preferences override organization preferences
- [ ] New users inherit organization defaults on account creation
- [ ] Organization preference changes don't affect existing user overrides
- [ ] Only organization admins can modify organization preferences

---

### REQ-NOTIF-FUNC-012: Notification Deletion

**Priority**: LOW
**Category**: Functional

WHEN a user deletes a notification, THE SYSTEM SHALL mark it as deleted and exclude it from queries.

**Acceptance Criteria**:
- [ ] API endpoint: DELETE /api/v1/notifications/{id}
- [ ] Soft-deletes notification (sets deleted_at timestamp)
- [ ] User can only delete their own notifications
- [ ] Deleted notifications not included in API responses
- [ ] Deleted notifications excluded from unread count

---

## Non-Functional Requirements

### REQ-NOTIF-PERF-001: Notification Creation Latency

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL create notification records in the database with P95 latency < 500ms from event trigger.

**Metrics**:
- P50 latency: < 100ms
- P95 latency: < 500ms
- P99 latency: < 1000ms

---

### REQ-NOTIF-PERF-002: WebSocket Delivery Latency

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL deliver notifications via WebSocket with P95 latency < 5 seconds from event trigger.

**Metrics**:
- P50 latency: < 1s
- P95 latency: < 5s
- Success rate: > 99%

---

### REQ-NOTIF-PERF-003: Query Performance

**Priority**: MEDIUM
**Category**: Performance

THE SYSTEM SHALL return notification list queries with P95 latency < 200ms.

**Metrics**:
- P50 latency: < 50ms
- P95 latency: < 200ms
- Max result set: 100 notifications

---

### REQ-NOTIF-SEC-001: Authorization

**Priority**: HIGH
**Category**: Security

THE SYSTEM SHALL only allow users to access their own notifications and preferences.

**Acceptance Criteria**:
- [ ] All notification endpoints require valid authentication
- [ ] Queries filter by user_id from JWT token
- [ ] Cross-user notification access returns 403 Forbidden
- [ ] Admin users can access notifications for debugging via separate endpoint

---

### REQ-NOTIF-SEC-002: Data Privacy

**Priority**: MEDIUM
**Category**: Privacy

THE SYSTEM SHALL not expose sensitive data in notification messages.

**Acceptance Criteria**:
- [ ] Notification messages don't include passwords, API keys, or tokens
- [ ] Error messages in notifications are sanitized
- [ ] User data in notifications respects data minimization principle

---

### REQ-NOTIF-AVAIL-001: Async Delivery

**Priority**: HIGH
**Category**: Availability

THE SYSTEM SHALL deliver notifications asynchronously without blocking the event that triggered them.

**Acceptance Criteria**:
- [ ] Notification creation uses background task queue
- [ ] Event processing continues if notification service is degraded
- [ ] Failed notification deliveries are queued for retry
- [ ] Service can handle temporary database unavailability

---

## Traceability

| Requirement ID | PRD Section | Design Section | Ticket |
|----------------|-------------|----------------|--------|
| REQ-NOTIF-FUNC-001 | User Stories #1-6 | Data Model, NotificationService | TKT-001 |
| REQ-NOTIF-FUNC-002 | User Stories #1-6 | WebSocket Integration | TKT-002 |
| REQ-NOTIF-FUNC-003 | User Stories | API Endpoints | TKT-002 |
| REQ-NOTIF-FUNC-004 | User Stories #1 | API Endpoints | TKT-002 |
| REQ-NOTIF-FUNC-005 | User Stories | API Endpoints | TKT-002 |
| REQ-NOTIF-FUNC-006 | Goals | NotificationService | TKT-001 |
| REQ-NOTIF-FUNC-007 | User Stories #6 | Preferences, Data Model | TKT-003 |
| REQ-NOTIF-FUNC-008 | Scope | EmailService | TKT-004 |
| REQ-NOTIF-FUNC-009 | Risks | NotificationService | TKT-001 |
| REQ-NOTIF-FUNC-010 | Risks | CleanupJob | TKT-001 |
| REQ-NOTIF-FUNC-011 | User Stories #6 | Organization Preferences | TKT-003 |
| REQ-NOTIF-FUNC-012 | Scope | API Endpoints | TKT-002 |
| REQ-NOTIF-PERF-001 | Success Metrics | Performance | TKT-001 |
| REQ-NOTIF-PERF-002 | Success Metrics | WebSocket | TKT-002 |
| REQ-NOTIF-PERF-003 | Success Metrics | API | TKT-002 |
| REQ-NOTIF-SEC-001 | Constraints | API Security | TKT-002 |
| REQ-NOTIF-SEC-002 | Constraints | Data Sanitization | TKT-001 |
| REQ-NOTIF-AVAIL-001 | Constraints | Async Architecture | All |
