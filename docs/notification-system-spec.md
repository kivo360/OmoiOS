# Real-Time Notification System - Requirements Specification

## 1. Overview

**Project Name:** Real-Time Notification System
**Version:** 1.0.0
**Status:** Requirements Analysis
**Last Updated:** 2026-01-08

### 1.1 Purpose
This specification defines the requirements for implementing a comprehensive real-time notification system for the OmoiOS platform. The system will provide multi-channel notification delivery including push notifications, in-app alerts, and email digests with user preferences and notification scheduling.

### 1.2 Scope
- Real-time push notifications (web and mobile)
- In-app notification center with real-time updates
- Email digest notifications (instant, daily, weekly)
- User notification preferences management
- Notification scheduling and delivery
- Notification history and read status tracking
- Notification templates and localization
- Notification rate limiting and batching
- Notification analytics and delivery status

### 1.3 Technology Stack
- **Backend Framework:** FastAPI
- **Database:** Supabase (PostgreSQL) with pgvector for notification history
- **Real-time Communication:** WebSocket (native FastAPI WebSocket or Socket.IO)
- **Push Notifications:** Firebase Cloud Messaging (FCM) for web/mobile
- **Email Service:** Resend (already integrated)
- **Message Queue:** TaskIQ with Redis (already integrated)
- **Frontend:** React/TypeScript with WebSocket client
- **Caching:** Redis (already integrated)

---

## 2. Functional Requirements

### 2.1 Notification Types

**REQ-001: Notification Type Classification**
- **WHEN** defining notification types,
- **THE SYSTEM SHALL** support:
  - **System Notifications:** Platform updates, maintenance alerts
  - **User Notifications:** Mentions, replies, likes, follows
  - **Task Notifications:** Task assignments, updates, completions, deadlines
  - **Security Notifications:** Login alerts, password changes, suspicious activity
  - **Billing Notifications:** Invoices, payment confirmations, subscription updates
  - **Workflow Notifications:** Spec approvals, phase transitions, ticket assignments
  - **Agent Notifications:** Agent completion, failures, status changes

**REQ-002: Notification Priority Levels**
- **WHEN** creating a notification,
- **THE SYSTEM SHALL** support priority levels:
  - **Critical:** Immediate delivery across all channels (security alerts)
  - **High:** Immediate push + in-app, optional email (task assignments)
  - **Normal:** In-app + push, optional digest (mentions, replies)
  - **Low:** In-app only, digest only (likes, follows)

### 2.2 Notification Creation

**REQ-003: Notification Creation**
- **WHEN** an event triggers a notification,
- **THE SYSTEM SHALL**:
  - Validate notification payload structure
  - Assign appropriate priority level
  - Determine target users/segments
  - Generate unique notification ID
  - Store notification in database
  - Enqueue notification for delivery
  - Return 202 (Accepted) for async delivery
  - Return 422 for validation errors

**REQ-004: Notification Template Rendering**
- **WHEN** rendering notification content,
- **THE SYSTEM SHALL**:
  - Support Jinja2 templates for content
  - Support multiple languages (i18n)
  - Support variable substitution
  - Support rich content (markdown, HTML for email)
  - Fall back to default template if specified template missing
  - Cache compiled templates

**REQ-005: Bulk Notification Creation**
- **WHEN** sending notifications to multiple users,
- **THE SYSTEM SHALL**:
  - Accept user list or segment criteria
  - Validate recipient count (max 10,000 per batch)
  - Create individual notification records per user
  - Batch enqueue for delivery
  - Return batch processing status
  - Return 400 if recipient count exceeds limit

### 2.3 Push Notifications

**REQ-006: Web Push Notification Delivery**
- **WHEN** delivering web push notifications,
- **THE SYSTEM SHALL**:
  - Use Web Push Protocol (VAPID)
  - Validate push subscription validity
  - Format payload according to Web Push standard
  - Handle TTL (time-to-live) for undelivered notifications
  - Retry failed deliveries with exponential backoff
  - Track delivery status (sent, delivered, failed)
  - Remove invalid subscriptions after 3 consecutive failures

**REQ-007: Mobile Push Notification Delivery**
- **WHEN** delivering mobile push notifications,
- **THE SYSTEM SHALL**:
  - Use Firebase Cloud Messaging (FCM)
  - Support both iOS (APNs via FCM) and Android
  - Handle notification categories and actions
  - Support badge count updates
  - Support sound customization
  - Handle silent notifications for data sync
  - Track delivery status per device token

**REQ-008: Push Subscription Management**
- **WHEN** a user subscribes to push notifications,
- **THE SYSTEM SHALL**:
  - Validate VAPID keys or FCM token
  - Store subscription with device metadata
  - Associate subscription with user
  - Generate unique subscription ID
  - Support multiple devices per user
  - Return subscription details

**REQ-009: Push Unsubscription**
- **WHEN** a user unsubscribes from push notifications,
- **THE SYSTEM SHALL**:
  - Remove or disable subscription record
  - Clean up invalid device tokens
  - Log unsubscription event
  - Return 204 No Content

### 2.4 In-App Notifications

**REQ-010: Real-Time In-App Delivery**
- **WHEN** delivering in-app notifications,
- **THE SYSTEM SHALL**:
  - Use WebSocket connections for real-time delivery
  - Broadcast to user's active sessions
  - Handle multiple concurrent sessions per user
  - Reconnect automatically on connection loss
  - Queue notifications for offline users
  - Deliver queued notifications on reconnection
  - Use heartbeat/ping for connection health

**REQ-011: Notification Center**
- **WHEN** a user views their notification center,
- **THE SYSTEM SHALL**:
  - Return paginated list of notifications
  - Support filtering by type, priority, read status
  - Support sorting (newest, oldest, priority)
  - Include unread count
  - Support cursor-based pagination for infinite scroll
  - Return 200 with notification list

**REQ-012: Notification Read Status**
- **WHEN** a user reads or marks a notification,
- **THE SYSTEM SHALL**:
  - Update read_at timestamp
  - Decrement unread count
  - Broadcast read status update to user's sessions
  - Support marking individual notifications
  - Support marking all as read
  - Return 200 on success

**REQ-013: Notification Actions**
- **WHEN** a notification includes actionable buttons,
- **THE SYSTEM SHALL**:
  - Support custom action buttons (accept, decline, view, etc.)
  - Execute action on button click
  - Track action clicks
  - Update notification status based on action
  - Return action result

### 2.5 Email Notifications

**REQ-014: Instant Email Delivery**
- **WHEN** delivering instant email notifications,
- **THE SYSTEM SHALL**:
  - Send immediately (within 5 seconds)
  - Use transactional email templates
  - Support HTML and plain text versions
  - Include unsubscribe link
  - Include privacy policy link
  - Track delivery status (sent, delivered, opened, clicked)
  - Handle bounce and complaint notifications

**REQ-015: Email Digest Creation**
- **WHEN** generating email digests,
- **THE SYSTEM SHALL**:
  - Aggregate notifications by digest period
  - Group notifications by type
  - Support daily digest (configurable time)
  - Support weekly digest (configurable day/time)
  - Include summary statistics (X new notifications)
  - Include direct links to notifications
  - Honor user's digest frequency preference

**REQ-016: Digest Scheduling**
- **WHEN** scheduling digest emails,
- **THE SYSTEM SHALL**:
  - Use TaskIQ scheduled tasks
  - Schedule per user's timezone
  - Skip if no new notifications
  - Retry on failure with backoff
  - Track last sent timestamp

### 2.6 User Preferences

**REQ-017: Notification Channel Preferences**
- **WHEN** a user configures notification channels,
- **THE SYSTEM SHALL**:
  - Support per-type channel preferences
  - Support enabling/disabling push
  - Support enabling/disabling email
  - Support enabling/disabling in-app (always on)
  - Support "all" or "none" global settings
  - Validate at least one channel is enabled
  - Return 200 with updated preferences

**REQ-018: Digest Frequency Preferences**
- **WHEN** a user sets digest frequency,
- **THE SYSTEM SHALL**:
  - Support "instant" (no digest)
  - Support "daily" (configurable time)
  - Support "weekly" (configurable day/time)
  - Support "never" (email off)
  - Support per-type digest settings
  - Default to "daily" at 9:00 AM user timezone

**REQ-019: Quiet Hours**
- **WHEN** a user sets quiet hours,
- **THE SYSTEM SHALL**:
  - Support start/end time configuration
  - Mute non-critical push notifications
  - Still deliver critical (security) notifications
  - Support timezone-aware scheduling
  - Support per-day configuration (weekdays vs weekends)
  - Store in user preferences

### 2.7 Notification History

**REQ-020: Notification History Query**
- **WHEN** querying notification history,
- **THE SYSTEM SHALL**:
  - Return paginated list of past notifications
  - Support date range filtering
  - Support filtering by type, status
  - Include delivery status per channel
  - Include read status
  - Support export (CSV, JSON)
  - Retain history for 90 days

**REQ-021: Notification Analytics**
- **WHEN** generating notification analytics,
- **THE SYSTEM SHALL**:
  - Track delivery rates per channel
  - Track open rates (email, push)
  - Track click-through rates
  - Aggregate by notification type
  - Aggregate by time period (hour, day, week, month)
  - Return analytics data via API

### 2.8 Rate Limiting

**REQ-022: Per-User Rate Limiting**
- **WHEN** sending notifications to a user,
- **THE SYSTEM SHALL**:
  - Limit to 10 push notifications per hour per user
  - Limit to 100 in-app notifications per hour per user
  - Limit to 20 email notifications per day per user
  - Queue excess notifications for later delivery
  - Priority notifications bypass limits
  - Return 429 if queue is full

**REQ-023: Global Rate Limiting**
- **WHEN** sending bulk notifications,
- **THE SYSTEM SHALL**:
  - Limit to 10,000 notifications per minute globally
  - Use token bucket algorithm
  - Throttle if limit exceeded
  - Provide rate limit status in response headers
  - Support admin override for critical announcements

---

## 3. Security Requirements

### 3.1 Data Protection

**SEC-001: Notification Content Security**
- **WHEN** storing notification content,
- **THE SYSTEM SHALL**:
  - Sanitize HTML content to prevent XSS
  - Mask sensitive data in notifications
  - Never include passwords or tokens in notifications
  - Encrypt sensitive notification data at rest
  - Use parameterized queries for database operations

**SEC-002: User Privacy**
- **THE SYSTEM SHALL**:
  - Require authentication for notification access
  - Only return notifications for authenticated user
  - Validate user ownership on all notification operations
  - Mask PII in logs
  - Support GDPR right to erasure for notification history

**SEC-003: Push Subscription Security**
- **WHEN** storing push subscriptions,
- **THE SYSTEM SHALL**:
  - Validate subscription ownership
  - Use VAPID keys for web push authentication
  - Rotate VAPID keys every 30 days
  - Never expose other users' subscriptions
  - Encrypt FCM tokens at rest

### 3.2 Access Control

**SEC-004: Notification Authorization**
- **THE SYSTEM SHALL**:
  - Require valid JWT for all notification endpoints
  - Validate user has permission to access notification
  - Use Row Level Security (RLS) in database
  - Log unauthorized access attempts
  - Implement proper CORS for WebSocket connections

### 3.3 OWASP Compliance

**SEC-005: OWASP Protection**
- **THE SYSTEM SHALL** protect against:
  - A01: Broken Access Control - proper user isolation
  - A03: Injection - sanitized notification content
  - A07: Authentication Failures - proper JWT validation
  - A09: Security Logging - audit all notification events

---

## 4. Data Model

### 4.1 Database Schema

#### `notifications` Table
```sql
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL, -- 'system', 'user', 'task', 'security', 'billing', 'workflow', 'agent'
    priority VARCHAR(20) NOT NULL DEFAULT 'normal', -- 'critical', 'high', 'normal', 'low'
    title VARCHAR(255) NOT NULL,
    body TEXT NOT NULL,
    data JSONB DEFAULT '{}', -- Additional data (action URLs, metadata, etc.)
    template_id VARCHAR(100), -- Reference to template used
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP, -- Optional expiry for time-sensitive notifications
    deleted_at TIMESTAMP -- Soft delete
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_type ON notifications(type);
CREATE INDEX idx_notifications_priority ON notifications(priority);
CREATE INDEX idx_notifications_read_at ON notifications(read_at) WHERE read_at IS NULL;
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
```

#### `notification_deliveries` Table
```sql
CREATE TABLE notification_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    channel VARCHAR(20) NOT NULL, -- 'push', 'in_app', 'email'
    status VARCHAR(20) NOT NULL DEFAULT 'pending', -- 'pending', 'sent', 'delivered', 'failed', 'bounced'
    device_id UUID REFERENCES push_subscriptions(id) ON DELETE SET NULL,
    error_message TEXT,
    sent_at TIMESTAMP,
    delivered_at TIMESTAMP,
    failed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notification_deliveries_notification_id ON notification_deliveries(notification_id);
CREATE INDEX idx_notification_deliveries_status ON notification_deliveries(status);
CREATE INDEX idx_notification_deliveries_channel ON notification_deliveries(channel);
```

#### `push_subscriptions` Table
```sql
CREATE TABLE push_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    p256dh_key VARCHAR(255) NOT NULL, -- VAPID for web push
    auth_key VARCHAR(255) NOT NULL,
    fcm_token VARCHAR(255), -- For mobile push
    device_info JSONB DEFAULT '{}', -- {platform, os, app_version, device_name}
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_push_subscriptions_user_id ON push_subscriptions(user_id);
CREATE INDEX idx_push_subscriptions_is_active ON push_subscriptions(is_active);
CREATE INDEX idx_push_subscriptions_fcm_token ON push_subscriptions(fcm_token);
```

#### `notification_preferences` Table
```sql
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type VARCHAR(50) NOT NULL,
    push_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT TRUE,
    in_app_enabled BOOLEAN DEFAULT TRUE,
    digest_frequency VARCHAR(20) DEFAULT 'instant', -- 'instant', 'daily', 'weekly', 'never'
    digest_time TIME DEFAULT '09:00:00', -- For daily digest
    digest_day INTEGER DEFAULT 1, -- For weekly digest (1=Monday, 7=Sunday)
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    quiet_hours_days JSONB DEFAULT '[1,2,3,4,5]', -- Days with quiet hours
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, notification_type)
);

CREATE INDEX idx_notification_preferences_user_id ON notification_preferences(user_id);
```

#### `notification_templates` Table
```sql
CREATE TABLE notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    title_template TEXT NOT NULL, -- Jinja2 template
    body_template TEXT NOT NULL, -- Jinja2 template
    email_subject_template TEXT,
    email_html_template TEXT,
    email_text_template TEXT,
    push_title_template TEXT,
    push_body_template TEXT,
    default_priority VARCHAR(20) DEFAULT 'normal',
    default_channels JSONB DEFAULT '["push", "in_app"]', -- Default enabled channels
    variables JSONB DEFAULT '{}', -- Schema of expected variables
    language VARCHAR(10) DEFAULT 'en',
    is_active BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notification_templates_type ON notification_templates(type);
CREATE INDEX idx_notification_templates_language ON notification_templates(language);
```

#### `email_digests` Table
```sql
CREATE TABLE email_digests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    frequency VARCHAR(20) NOT NULL, -- 'daily', 'weekly'
    scheduled_for TIMESTAMP NOT NULL,
    sent_at TIMESTAMP,
    notification_ids UUID[] DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'sent', 'failed'
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_email_digests_user_id ON email_digests(user_id);
CREATE INDEX idx_email_digests_scheduled_for ON email_digests(scheduled_for);
CREATE INDEX idx_email_digests_status ON email_digests(status);
```

#### `notification_analytics` Table
```sql
CREATE TABLE notification_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID REFERENCES notifications(id) ON DELETE SET NULL,
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    event VARCHAR(50) NOT NULL, -- 'sent', 'delivered', 'opened', 'clicked', 'bounced'
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    device_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notification_analytics_notification_id ON notification_analytics(notification_id);
CREATE INDEX idx_notification_analytics_type ON notification_analytics(notification_type);
CREATE INDEX idx_notification_analytics_event ON notification_analytics(event);
CREATE INDEX idx_notification_analytics_created_at ON notification_analytics(created_at);
```

### 4.2 Environment Variables

```bash
# WebSocket Configuration
WS_ENABLED=true
WS_HOST=0.0.0.0
WS_PORT=8001
WS_HEARTBEAT_INTERVAL=30
WS_MAX_CONNECTIONS=10000

# Push Notification Configuration
# Web Push (VAPID)
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=mailto:admin@yourapp.com

# Firebase Cloud Messaging
FCM_SERVER_KEY=
FCM_PROJECT_ID=

# Email Configuration (using Resend - already integrated)
RESEND_API_KEY=
RESEND_FROM_EMAIL=noreply@yourapp.com
RESEND_FROM_NAME="OmoiOS"

# Redis (for TaskIQ and caching - already integrated)
REDIS_URL=redis://localhost:6379/0

# Notification Settings
NOTIFICATION_RETENTION_DAYS=90
NOTIFICATION_MAX_BATCH_SIZE=10000
NOTIFICATION_QUEUE_SIZE=100000

# Rate Limiting
RATE_LIMIT_PUSH_PER_HOUR=10
RATE_LIMIT_IN_APP_PER_HOUR=100
RATE_LIMIT_EMAIL_PER_DAY=20
RATE_LIMIT_GLOBAL_PER_MINUTE=10000

# Digest Settings
DIGEST_DEFAULT_TIME=09:00
DIGEST_DEFAULT_DAY=1
DIGEST_TIMEZONE=UTC

# Security
NOTIFICATION_ENCRYPTION_KEY=
```

---

## 5. API Specification

### 5.1 REST API Endpoints

#### POST /api/v1/notifications
Create a new notification (internal/service endpoint).

**Headers:**
```
Authorization: Bearer <service_token>
X-Service-Auth: <internal_service_key>
```

**Request Body:**
```json
{
  "user_id": "uuid",
  "type": "task",
  "priority": "high",
  "title": "New Task Assigned",
  "body": "You have been assigned a new task: 'Review PR #123'",
  "data": {
    "task_id": "uuid",
    "action_url": "/tasks/uuid",
    "actions": [
      {"label": "View", "url": "/tasks/uuid", "primary": true},
      {"label": "Dismiss", "action": "dismiss"}
    ]
  },
  "template_id": "task_assigned"
}
```

**Response 202:**
```json
{
  "id": "uuid",
  "status": "queued",
  "channels": ["push", "in_app", "email"],
  "created_at": "2026-01-08T12:00:00Z"
}
```

---

#### POST /api/v1/notifications/bulk
Create notifications for multiple users.

**Headers:**
```
Authorization: Bearer <service_token>
X-Service-Auth: <internal_service_key>
```

**Request Body:**
```json
{
  "user_ids": ["uuid1", "uuid2", "uuid3"],
  "type": "system",
  "priority": "high",
  "title": "System Maintenance",
  "body": "Scheduled maintenance will begin in 1 hour",
  "data": {},
  "send_email": true
}
```

**Response 202:**
```json
{
  "batch_id": "uuid",
  "recipient_count": 3,
  "status": "processing"
}
```

---

#### GET /api/v1/notifications
Get user's notifications.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
- `type`: Filter by type (optional)
- `priority`: Filter by priority (optional)
- `is_read`: Filter read status (true/false, optional)
- `limit`: Results per page (default: 20, max: 100)
- `cursor`: Pagination cursor

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "type": "task",
      "priority": "high",
      "title": "New Task Assigned",
      "body": "You have been assigned a new task",
      "data": {
        "task_id": "uuid",
        "action_url": "/tasks/uuid"
      },
      "read_at": null,
      "created_at": "2026-01-08T12:00:00Z",
      "delivery_status": {
        "push": "delivered",
        "in_app": "delivered",
        "email": "sent"
      }
    }
  ],
  "unread_count": 5,
  "next_cursor": "cursor_string",
  "has_more": true
}
```

---

#### GET /api/v1/notifications/{notification_id}
Get specific notification.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "id": "uuid",
  "type": "task",
  "priority": "high",
  "title": "New Task Assigned",
  "body": "You have been assigned a new task",
  "data": {
    "task_id": "uuid",
    "action_url": "/tasks/uuid",
    "actions": [...]
  },
  "read_at": "2026-01-08T12:05:00Z",
  "created_at": "2026-01-08T12:00:00Z",
  "delivery_status": {...}
}
```

---

#### PATCH /api/v1/notifications/{notification_id}/read
Mark notification as read.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "id": "uuid",
  "read_at": "2026-01-08T12:05:00Z"
}
```

---

#### POST /api/v1/notifications/read-all
Mark all notifications as read.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "updated_count": 15
}
```

---

#### DELETE /api/v1/notifications/{notification_id}
Delete notification.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 204:** No Content

---

#### GET /api/v1/notifications/unread-count
Get unread notification count.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "count": 5,
  "by_type": {
    "task": 2,
    "user": 2,
    "system": 1
  }
}
```

---

### 5.2 Push Subscription Endpoints

#### POST /api/v1/notifications/push/subscribe
Subscribe to push notifications.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body (Web Push):**
```json
{
  "subscription": {
    "endpoint": "https://fcm.googleapis.com/...",
    "keys": {
      "p256dh": "key...",
      "auth": "auth..."
    }
  },
  "device_info": {
    "platform": "web",
    "user_agent": "Mozilla/5.0...",
    "screen_width": 1920
  }
}
```

**Request Body (Mobile):**
```json
{
  "fcm_token": "firebase_device_token",
  "device_info": {
    "platform": "ios",
    "os_version": "17.0",
    "app_version": "1.0.0",
    "device_name": "iPhone 14"
  }
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "is_active": true,
  "created_at": "2026-01-08T12:00:00Z"
}
```

---

#### DELETE /api/v1/notifications/push/unsubscribe
Unsubscribe from push notifications.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "subscription_id": "uuid"
}
```

**Response 204:** No Content

---

#### GET /api/v1/notifications/push/subscriptions
Get user's push subscriptions.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "endpoint": "https://fcm.googleapis.com/...",
      "device_info": {
        "platform": "web",
        "device_name": "Chrome on Windows"
      },
      "is_active": true,
      "last_used_at": "2026-01-08T12:00:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

### 5.3 Preferences Endpoints

#### GET /api/v1/notifications/preferences
Get user's notification preferences.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "items": [
    {
      "notification_type": "task",
      "push_enabled": true,
      "email_enabled": true,
      "in_app_enabled": true,
      "digest_frequency": "instant",
      "digest_time": "09:00:00",
      "digest_day": 1,
      "quiet_hours_start": "22:00:00",
      "quiet_hours_end": "08:00:00",
      "quiet_hours_days": [1, 2, 3, 4, 5]
    }
  ]
}
```

---

#### PUT /api/v1/notifications/preferences/{notification_type}
Update notification preferences for a type.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "push_enabled": true,
  "email_enabled": false,
  "digest_frequency": "daily",
  "digest_time": "09:00:00",
  "quiet_hours_start": "22:00:00",
  "quiet_hours_end": "08:00:00"
}
```

**Response 200:**
```json
{
  "notification_type": "task",
  "push_enabled": true,
  "email_enabled": false,
  "digest_frequency": "daily",
  "updated_at": "2026-01-08T12:00:00Z"
}
```

---

#### PUT /api/v1/notifications/preferences/global
Update global notification preferences.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request Body:**
```json
{
  "all_push_enabled": true,
  "all_email_enabled": true,
  "default_digest_frequency": "daily",
  "default_digest_time": "09:00:00"
}
```

**Response 200:** Updated preferences

---

### 5.4 WebSocket Events

#### Connection
```
WS /api/v1/notifications/ws
```

**Query Parameters:**
- `token`: JWT access token

**Client -> Server:**
```json
{
  "type": "authenticate",
  "token": "jwt_token"
}
```

**Server -> Client:**
```json
{
  "type": "authenticated",
  "user_id": "uuid"
}
```

---

#### Notification Received
**Server -> Client:**
```json
{
  "type": "notification",
  "data": {
    "id": "uuid",
    "type": "task",
    "priority": "high",
    "title": "New Task Assigned",
    "body": "You have been assigned a new task",
    "data": {
      "action_url": "/tasks/uuid"
    },
    "created_at": "2026-01-08T12:00:00Z"
  }
}
```

---

#### Mark as Read
**Client -> Server:**
```json
{
  "type": "mark_read",
  "notification_id": "uuid"
}
```

**Server -> Client:**
```json
{
  "type": "read_status_updated",
  "notification_id": "uuid",
  "read_at": "2026-01-08T12:05:00Z",
  "unread_count": 4
}
```

---

#### Unread Count Update
**Server -> Client (broadcast):**
```json
{
  "type": "unread_count",
  "count": 5,
  "by_type": {
    "task": 2,
    "user": 2,
    "system": 1
  }
}
```

---

#### Heartbeat
**Client -> Server (every 30s):**
```json
{
  "type": "ping"
}
```

**Server -> Client:**
```json
{
  "type": "pong",
  "timestamp": "2026-01-08T12:00:00Z"
}
```

---

#### Error
**Server -> Client:**
```json
{
  "type": "error",
  "code": "AUTH_FAILED",
  "message": "Invalid or expired token"
}
```

---

### 5.5 Internal Service Endpoints

#### POST /api/v1/internal/notifications/send
Internal endpoint for services to send notifications.

**Headers:**
```
X-Internal-Service-Key: <service_key>
X-Service-Name: <service_name>
```

**Request Body:**
```json
{
  "user_id": "uuid",
  "type": "task",
  "priority": "high",
  "title": "Task Updated",
  "body": "Task status changed to 'In Progress'",
  "data": {
    "task_id": "uuid",
    "old_status": "todo",
    "new_status": "in_progress"
  },
  "channels": ["push", "in_app"]
}
```

**Response 202:**
```json
{
  "notification_id": "uuid",
  "status": "queued"
}
```

---

## 6. Implementation Tasks

### Phase 1: Foundation (Week 1)

#### Task 1.1: Database Setup
- [ ] Create notification tables (notifications, notification_deliveries, push_subscriptions, notification_preferences, notification_templates, email_digests, notification_analytics)
- [ ] Set up Row Level Security (RLS) policies
- [ ] Create database indexes
- [ ] Write Alembic migration scripts
- [ ] Set up database connection pooling

**Priority:** High
**Dependencies:** None
**Estimated Complexity:** Medium

#### Task 1.2: Project Structure
- [ ] Create `backend/app/api/v1/notifications/` directory structure
- [ ] Create `backend/app/services/notification_service.py`
- [ ] Create `backend/app/services/push_service.py`
- [ ] Create `backend/app/services/email_digest_service.py`
- [ ] Create `backend/app/models/notification.py` database models
- [ ] Create `backend/app/schemas/notification.py` Pydantic schemas
- [ ] Create `backend/app/api/dependencies.py` notification dependencies

**Priority:** High
**Dependencies:** None
**Estimated Complexity:** Low

#### Task 1.3: Configuration Setup
- [ ] Set up WebSocket configuration
- [ ] Set up VAPID key generation and storage
- [ ] Set up FCM configuration
- [ ] Set up notification rate limit configuration
- [ ] Set up digest scheduling configuration
- [ ] Load environment variables

**Priority:** High
**Dependencies:** Task 1.2
**Estimated Complexity:** Low

---

### Phase 2: Core Notification Service (Week 1-2)

#### Task 2.1: Notification Creation
- [ ] Implement notification creation endpoint
- [ ] Validate notification payload
- [ ] Implement template rendering (Jinja2)
- [ ] Store notification in database
- [ ] Enqueue notification for delivery
- [ ] Implement bulk notification creation

**Priority:** High
**Dependencies:** Task 1.2
**Estimated Complexity:** Medium

#### Task 2.2: Notification Templates
- [ ] Create default notification templates
- [ ] Implement template caching
- [ ] Add template versioning
- [ ] Support multi-language templates
- [ ] Create template management endpoints

**Priority:** Medium
**Dependencies:** Task 1.2
**Estimated Complexity:** Medium

#### Task 2.3: Notification Query
- [ ] Implement GET /notifications endpoint
- [ ] Implement filtering (type, priority, read status)
- [ ] Implement sorting
- [ ] Implement cursor-based pagination
- [ ] Implement unread count endpoint
- [ ] Optimize queries with proper indexes

**Priority:** High
**Dependencies:** Task 1.2
**Estimated Complexity:** Medium

---

### Phase 3: Push Notifications (Week 2)

#### Task 3.1: Web Push Integration
- [ ] Implement VAPID key generation
- [ ] Integrate Web Push library
- [ ] Implement push subscription management
- [ ] Implement web push delivery
- [ ] Handle delivery failures and retries
- [ ] Clean up invalid subscriptions

**Priority:** High
**Dependencies:** Task 1.3
**Estimated Complexity:** High

#### Task 3.2: FCM Integration
- [ ] Set up Firebase Admin SDK
- [ ] Implement FCM token registration
- [ ] Implement FCM notification delivery
- [ ] Support iOS and Android specific settings
- [ ] Handle badge count and sounds
- [ ] Support silent notifications

**Priority:** High
**Dependencies:** Task 1.3
**Estimated Complexity:** High

#### Task 3.3: Push Delivery Worker
- [ ] Create TaskIQ worker for push delivery
- [ ] Implement retry logic with exponential backoff
- [ ] Track delivery status
- [ ] Handle rate limiting
- [ ] Batch delivery for efficiency

**Priority:** High
**Dependencies:** Task 3.1, Task 3.2
**Estimated Complexity:** Medium

---

### Phase 4: In-App Notifications (Week 2-3)

#### Task 4.1: WebSocket Server
- [ ] Implement WebSocket endpoint
- [ ] Implement JWT authentication for WebSocket
- [ ] Handle connection management
- [ ] Implement heartbeat/ping-pong
- [ ] Handle reconnection logic
- [ ] Broadcast to user sessions

**Priority:** High
**Dependencies:** Task 1.3
**Estimated Complexity:** High

#### Task 4.2: Real-Time Delivery
- [ ] Implement notification broadcast via WebSocket
- [ ] Queue notifications for offline users
- [ ] Deliver queued notifications on reconnection
- [ ] Handle read status updates via WebSocket
- [ ] Broadcast unread count updates

**Priority:** High
**Dependencies:** Task 4.1
**Estimated Complexity:** Medium

#### Task 4.3: Read Status Management
- [ ] Implement mark as read endpoint
- [ ] Implement mark all as read endpoint
- [ ] Broadcast read status to user sessions
- [ ] Update unread count
- [ ] Handle soft delete

**Priority:** High
**Dependencies:** Task 4.1
**Estimated Complexity:** Low

---

### Phase 5: Email Digests (Week 3)

#### Task 5.1: Email Templates
- [ ] Create digest email templates (HTML and plain text)
- [ ] Create instant email templates
- [ ] Support variable substitution
- [ ] Include unsubscribe links
- [ ] Support multiple languages

**Priority:** High
**Dependencies:** Task 2.2
**Estimated Complexity:** Medium

#### Task 5.2: Instant Email Delivery
- [ ] Integrate with Resend (already in project)
- [ ] Implement instant email delivery
- [ ] Track delivery status
- [ ] Handle bounces and complaints
- [ ] Implement click/open tracking

**Priority:** High
**Dependencies:** Task 5.1
**Estimated Complexity:** Medium

#### Task 5.3: Digest Scheduling
- [ ] Create TaskIQ scheduled tasks
- [ ] Implement daily digest scheduling
- [ ] Implement weekly digest scheduling
- [ ] Support user timezone
- [ ] Aggregate notifications by type
- [ ] Skip empty digests

**Priority:** Medium
**Dependencies:** Task 5.1
**Estimated Complexity:** High

#### Task 5.4: Digest Delivery Worker
- [ ] Create digest delivery worker
- [ ] Generate digest content
- [ ] Send digest emails
- [ ] Track delivery status
- [ ] Handle failures with retry

**Priority:** Medium
**Dependencies:** Task 5.3
**Estimated Complexity:** Medium

---

### Phase 6: User Preferences (Week 3-4)

#### Task 6.1: Preferences API
- [ ] Implement GET /preferences endpoint
- [ ] Implement PUT /preferences/{type} endpoint
- [ ] Implement PUT /preferences/global endpoint
- [ ] Add default preferences on user creation
- [ ] Validate at least one channel enabled

**Priority:** High
**Dependencies:** Task 1.2
**Estimated Complexity:** Low

#### Task 6.2: Channel Preferences
- [ ] Implement per-type channel preferences
- [ ] Apply preferences when sending notifications
- [ ] Support enable/disable per channel
- [ ] Support global enable/disable

**Priority:** High
**Dependencies:** Task 6.1
**Estimated Complexity:** Medium

#### Task 6.3: Digest Frequency
- [ ] Implement digest frequency settings
- [ ] Support instant, daily, weekly, never
- [ ] Apply frequency when scheduling digests
- [ ] Default to daily at 9 AM

**Priority:** Medium
**Dependencies:** Task 6.1
**Estimated Complexity:** Medium

#### Task 6.4: Quiet Hours
- [ ] Implement quiet hours configuration
- [ ] Support per-day quiet hours
- [ ] Mute non-critical notifications during quiet hours
- [ ] Always deliver critical notifications
- [ ] Support timezone-aware scheduling

**Priority:** Low
**Dependencies:** Task 6.1
**Estimated Complexity:** Medium

---

### Phase 7: Rate Limiting & Batching (Week 4)

#### Task 7.1: Rate Limiting
- [ ] Implement per-user rate limits
- [ ] Use Redis for distributed rate limiting
- [ ] Implement token bucket algorithm
- [ ] Queue excess notifications
- [ ] Return 429 when limits exceeded
- [ ] Critical notifications bypass limits

**Priority:** High
**Dependencies:** Task 1.3
**Estimated Complexity:** Medium

#### Task 7.2: Notification Batching
- [ ] Implement batch notification creation
- [ ] Validate batch size limits
- [ ] Optimize database inserts
- [ ] Return batch processing status
- [ ] Support async batch processing

**Priority:** Medium
**Dependencies:** Task 2.1
**Estimated Complexity:** Medium

#### Task 7.3: Global Throttling
- [ ] Implement global rate limit
- [ ] Throttle bulk notifications
- [ ] Provide rate limit headers
- [ ] Support admin override

**Priority:** Medium
**Dependencies:** Task 7.1
**Estimated Complexity:** Low

---

### Phase 8: Analytics & History (Week 4)

#### Task 8.1: Notification History
- [ ] Implement history query endpoint
- [ ] Support date range filtering
- [ ] Support export (CSV, JSON)
- [ ] Implement retention policy (90 days)
- [ ] Archive old notifications

**Priority:** Medium
**Dependencies:** Task 2.3
**Estimated Complexity:** Low

#### Task 8.2: Analytics Tracking
- [ ] Track all delivery events
- [ ] Track open/click events
- [ ] Aggregate analytics by type
- [ ] Aggregate by time period
- [ ] Store in notification_analytics table

**Priority:** Medium
**Dependencies:** Task 3.3, Task 5.2
**Estimated Complexity:** Medium

#### Task 8.3: Analytics API
- [ ] Implement analytics query endpoint
- [ ] Return delivery rates
- [ ] Return open/click rates
- [ ] Support aggregation by period
- [ ] Support filtering by type

**Priority:** Low
**Dependencies:** Task 8.2
**Estimated Complexity:** Medium

---

### Phase 9: Frontend Integration (Week 5)

#### Task 9.1: WebSocket Client
- [ ] Create WebSocket connection manager
- [ ] Implement auto-reconnection
- [ ] Handle authentication
- [ ] Handle incoming notifications
- [ ] Handle read status updates

**Priority:** High
**Dependencies:** Phase 4
**Estimated Complexity:** High

#### Task 9.2: Push Notification UI
- [ ] Create notification bell icon
- [ ] Show unread count badge
- [ ] Create notification dropdown
- [ ] Implement notification list
- [ ] Support mark as read
- [ ] Support mark all as read

**Priority:** High
**Dependencies:** Task 9.1
**Estimated Complexity:** High

#### Task 9.3: Notification Center Page
- [ ] Create full notification center page
- [ ] Implement filtering and sorting
- [ ] Support pagination
- [ ] Show notification details
- [ ] Handle notification actions
- [ ] Support delete notifications

**Priority:** High
**Dependencies:** Task 9.2
**Estimated Complexity:** High

#### Task 9.4: Push Subscription
- [ ] Request push notification permission
- [ ] Subscribe to web push
- [ ] Handle subscription updates
- [ ] Handle unsubscription
- [ ] Store subscription in backend

**Priority:** High
**Dependencies:** Task 9.1
**Estimated Complexity:** Medium

#### Task 9.5: Preferences UI
- [ ] Create notification preferences page
- [ ] Implement channel toggles
- [ ] Implement digest frequency selector
- [ ] Implement quiet hours configuration
- [ ] Support per-type preferences

**Priority:** Medium
**Dependencies:** Task 9.1
**Estimated Complexity:** Medium

---

### Phase 10: Testing (Week 5-6)

#### Task 10.1: Unit Tests
- [ ] Test notification creation
- [ ] Test template rendering
- [ ] Test preference management
- [ ] Test rate limiting logic
- [ ] Test WebSocket message handling
- [ ] Mock external services (FCM, Resend)

**Priority:** High
**Dependencies:** Phase 1-9
**Estimated Complexity:** High

#### Task 10.2: Integration Tests
- [ ] Test notification delivery flow
- [ ] Test push subscription flow
- [ ] Test WebSocket connection flow
- [ ] Test email digest flow
- [ ] Test preference application
- [ ] Test rate limiting

**Priority:** High
**Dependencies:** Phase 1-9
**Estimated Complexity:** High

#### Task 10.3: End-to-End Tests
- [ ] Test full notification flow (creation to delivery)
- [ ] Test read status synchronization
- [ ] Test multi-session WebSocket
- [ ] Test digest scheduling
- [ ] Test preference changes

**Priority:** High
**Dependencies:** Phase 1-9
**Estimated Complexity:** High

#### Task 10.4: Load Tests
- [ ] Test WebSocket connection limits
- [ ] Test bulk notification creation
- [ ] Test concurrent notification delivery
- [ ] Test rate limiting under load
- [ ] Test database query performance

**Priority:** Medium
**Dependencies:** Phase 1-9
**Estimated Complexity:** High

---

### Phase 11: Security & Hardening (Week 6)

#### Task 11.1: Security Implementation
- [ ] Sanitize all notification content (XSS prevention)
- [ ] Implement RLS policies
- [ ] Encrypt sensitive data at rest
- [ ] Validate user ownership on all operations
- [ ] Mask PII in logs

**Priority:** High
**Dependencies:** Phase 1-10
**Estimated Complexity:** Medium

#### Task 11.2: VAPID Key Rotation
- [ ] Implement key rotation script
- [ ] Schedule key rotation (30 days)
- [ ] Update subscriptions with new keys
- [ ] Handle transition period

**Priority:** Medium
**Dependencies:** Task 3.1
**Estimated Complexity:** Medium

#### Task 11.3: Security Headers
- [ ] Configure CORS for WebSocket
- [ ] Add CSP headers
- [ ] Configure proper authentication

**Priority:** High
**Dependencies:** None
**Estimated Complexity:** Low

---

### Phase 12: Documentation & Deployment (Week 6)

#### Task 12.1: Documentation
- [ ] Write API documentation
- [ ] Write WebSocket protocol documentation
- [ ] Write setup guide for push notifications
- [ ] Write configuration guide
- [ ] Create architecture diagrams

**Priority:** Medium
**Dependencies:** Phase 1-11
**Estimated Complexity:** Low

#### Task 12.2: Deployment
- [ ] Configure production environment variables
- [ ] Set up FCM project
- [ ] Set up VAPID keys
- [ ] Configure Redis for production
- [ ] Set up monitoring and alerts
- [ ] Configure log aggregation

**Priority:** High
**Dependencies:** Phase 1-11
**Estimated Complexity:** Medium

#### Task 12.3: Monitoring
- [ ] Set up notification delivery metrics
- [ ] Set up WebSocket connection monitoring
- [ ] Set up alerting for delivery failures
- [ ] Create dashboards for analytics
- [ ] Monitor queue depths

**Priority:** High
**Dependencies:** Task 12.2
**Estimated Complexity:** Medium

---

## 7. Acceptance Criteria

### 7.1 Notification Creation
- [ ] System can create notifications with valid payload
- [ ] System validates notification structure
- [ ] System renders templates correctly
- [ ] System enqueues for delivery
- [ ] Bulk creation works for multiple users

### 7.2 Push Notifications
- [ ] Web push notifications are delivered
- [ ] FCM notifications are delivered to iOS
- [ ] FCM notifications are delivered to Android
- [ ] Invalid subscriptions are cleaned up
- [ ] Delivery status is tracked
- [ ] Failed deliveries are retried

### 7.3 In-App Notifications
- [ ] WebSocket connections work
- [ ] Notifications are delivered in real-time
- [ ] Multiple sessions receive notifications
- [ ] Reconnection works after disconnect
- [ ] Offline users receive queued notifications
- [ ] Read status syncs across sessions

### 7.4 Email Notifications
- [ ] Instant emails are sent immediately
- [ ] Daily digests are sent at configured time
- [ ] Weekly digests are sent on configured day
- [ ] Email templates render correctly
- [ ] Unsubscribe links work
- [ ] Delivery status is tracked

### 7.5 User Preferences
- [ ] Users can enable/disable channels
- [ ] Users can set digest frequency
- [ ] Users can configure quiet hours
- [ ] Preferences are applied to delivery
- [ ] Critical notifications bypass quiet hours

### 7.6 Rate Limiting
- [ ] Per-user limits are enforced
- [ ] Global limits are enforced
- [ ] Critical notifications bypass limits
- [ ] Excess notifications are queued
- [ ] 429 is returned when limits exceeded

### 7.7 Performance
- [ ] Notification creation < 100ms
- [ ] WebSocket delivery < 50ms
- [ ] Push delivery queued < 200ms
- [ ] Email delivery < 5 seconds
- [ ] Notification query < 200ms
- [ ] Support 10,000 concurrent WebSocket connections

### 7.8 Security
- [ ] All content is sanitized
- [ ] RLS policies are enforced
- [ ] Users can only access their notifications
- [ ] PII is masked in logs
- [ ] VAPID keys are rotated

---

## 8. Non-Functional Requirements

### 8.1 Performance
- Notification creation: < 100ms (p95)
- WebSocket message delivery: < 50ms (p95)
- Push notification queuing: < 200ms (p95)
- Email delivery: < 5 seconds (p95)
- Notification query: < 200ms (p95)
- Support 10,000 concurrent WebSocket connections
- Support 100,000 notifications per minute

### 8.2 Availability
- 99.9% uptime SLA
- Graceful degradation if push service is down
- Graceful degradation if email service is down
- WebSocket auto-reconnection
- Queue persistence for restart safety

### 8.3 Scalability
- Horizontal scaling for API servers
- Multiple TaskIQ workers
- Redis clustering for rate limiting
- Database connection pooling
- Stateless WebSocket routing

### 8.4 Reliability
- At-least-once delivery guarantee
- Retry with exponential backoff
- Dead letter queue for failed notifications
- Queue persistence in Redis

### 8.5 Maintainability
- Clean architecture with separation of concerns
- Comprehensive test coverage (> 80%)
- Clear code documentation
- Structured logging with correlation IDs
- Template-based notifications for easy updates

---

## 9. Future Enhancements (Out of Scope)

- Notification categories and channels
- Notification snoozing
- Notification aggregation (grouping similar notifications)
- Push notification action buttons (interactive notifications)
- SMS notifications
- Slack/Teams integration
- Webhook notifications
- Notification A/B testing
- Smart notification timing (AI-based)
- Notification sentiment analysis
- Rich media in notifications (images, videos)
- Voice notifications
- Location-based notifications
- Notification recommendations
- Dark mode for email templates
- User notification groups/segments
- Admin notification broadcast tool
- Notification performance dashboards

---

## 10. References

- [Web Push API](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)
- [Web Push Protocol](https://tools.ietf.org/html/rfc8030)
- [VAPID Specification](https://datatracker.ietf.org/doc/html/rfc8292)
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [TaskIQ Documentation](https://taskiq-python.github.io/)
- [Resend Email Documentation](https://resend.com/docs)

---

**Document Status:** Requirements Analysis
**Next Phase:** Design Approval
**Prepared by:** Claude Code
**Date:** 2026-01-08
