---
id: PRD-NOTIF-001
title: User Notification System PRD
feature: notification-system
created: 2026-01-08
updated: 2026-01-08
status: draft
author: Claude
---

# User Notification System

## Executive Summary

The User Notification System provides a comprehensive notification infrastructure for OmoiOS, enabling real-time delivery of important system events to users. This system fills a critical gap in the current platform where users must actively poll for updates rather than being proactively informed about relevant events. The notification system integrates with existing infrastructure (WebSocket, EventBus, Alert system) to deliver timely, actionable information through in-app notifications and optional email delivery.

## Problem Statement

### Current State
OmoiOS currently has no centralized user notification system. Users must manually check various pages to see:
- When tickets are assigned to them
- When tasks complete or fail
- When approval is requested
- System alerts and anomalies
- Agent status changes

The existing Alert system (`Alert`, `MonitorAnomaly` models) is focused on system-level monitoring rather than user-facing notifications. While WebSocket infrastructure exists, it only handles React Query cache invalidation without persistent notification records.

### Desired State
Users receive timely, persistent notifications for events relevant to them. Notifications are:
- **Delivered in real-time** via WebSocket for active users
- **Persisted** for later viewing (notification center)
- **Filtered** based on user preferences
- **Aggregated** to prevent spam
- **Trackable** (read/unread status, delivery confirmation)

### Impact of Not Building
- Users miss important events requiring their attention
- Increased friction in collaborative workflows
- Delayed response to critical issues
- Poor user experience compared to modern SaaS platforms

## Goals & Success Metrics

### Primary Goals
1. Enable real-time notification delivery for user-specific events
2. Provide a notification center for viewing historical notifications
3. Support user notification preferences (opt-in/opt-out by type)
4. Integrate with existing WebSocket infrastructure

### Success Metrics
| Metric | Current | Target | How Measured |
|--------|---------|--------|--------------|
| Time to notification delivery | N/A | < 5 seconds | P95 latency from event to WebSocket delivery |
| Notification delivery success rate | N/A | > 99% | Failed deliveries / total deliveries |
| User engagement with notifications | N/A | > 60% read rate | Read notifications / total notifications |
| Reduction in polling behavior | N/A | -40% | Page refresh rate before vs after |

## User Stories

### Primary User: Software Engineer

1. **Ticket Assignment Notification**
   As a software engineer, I want to be notified when a ticket is assigned to me so that I can immediately start working on it.

   Acceptance Criteria:
   - [ ] Real-time notification appears when ticket is assigned
   - [ ] Notification includes ticket title, project, and assigner
   - [ ] Clicking notification navigates to ticket detail page
   - [ ] Notification persists in notification center until read

2. **Task Completion Notification**
   As a software engineer, I want to be notified when my submitted tasks complete so that I can review results or take next steps.

   Acceptance Criteria:
   - [ ] Notification includes task status (success/failure)
   - [ ] Failed tasks include error message snippet
   - [ ] Success tasks include link to results

3. **Approval Request Notification**
   As a software engineer, I want to be notified when my approval is requested so that I don't block team progress.

   Acceptance Criteria:
   - [ ] Notification marked as "action required"
   - [ ] Includes approval deadline if applicable
   - [ ] Quick approve/reject buttons in notification

### Secondary User: Project Manager

4. **Agent Status Changes**
   As a project manager, I want to be notified when agents become unhealthy so that I can investigate issues.

   Acceptance Criteria:
   - [ ] Notifications for agent errors, timeouts
   - [ ] Can be filtered by severity
   - [ ] Includes link to agent diagnostics

5. **System Alerts**
   As a project manager, I want to be notified of critical system alerts so that I can respond to incidents.

   Acceptance Criteria:
   - [ ] Critical alerts trigger immediate notification
   - [ ] Non-critical alerts appear in notification center only
   - [ ] Can configure per-organization alert preferences

### Admin User

6. **Notification Management**
   As an admin, I want to manage notification preferences for my organization so that team members aren't overwhelmed.

   Acceptance Criteria:
   - [ ] Can set default notification preferences for organization
   - [ ] Can override user preferences for critical events
   - [ ] Can view notification delivery statistics

## Scope

### In Scope
- **Notification Types**: Ticket assigned/updated, task completed/failed, approval requested, agent status change, system alerts, mentions
- **Delivery Channels**: In-app (WebSocket), Email (optional)
- **User Preferences**: Opt-in/opt-out by notification type, per-channel preferences
- **Notification Center**: Persistent storage, read/unread tracking, filtering, pagination
- **Real-time Delivery**: WebSocket integration for instant delivery to active users
- **Aggregation**: Group similar notifications (e.g., "5 tickets assigned")
- **Rate Limiting**: Prevent notification spam (max 10/hour per user)
- **Organization-level Settings**: Default preferences for organizations

### Out of Scope
- **Push Notifications**: Mobile/browser push notifications (future phase)
- **External Integrations**: Slack, Discord, Microsoft Teams (future phase)
- **Notification Templates**: Customizable notification templates (future phase)
- **Scheduled/Digest Notifications**: Daily/weekly email digests (future phase)
- **Snoozing**: Temporarily disable notifications (future phase)
- **Do Not Disturb**: Time-based notification suppression (future phase)

### Future Considerations
- Push notification support for mobile apps
- Integration with communication platforms (Slack, Teams)
- Rich notification templates with attachments
- Notification analytics and insights
- A/B testing for notification effectiveness

## Constraints

### Technical Constraints
- Must integrate with existing WebSocket infrastructure at `/api/v1/ws/events`
- Must integrate with existing EventBusService for event subscription
- Must use PostgreSQL for notification storage
- Must respect existing authentication/authorization (Supabase JWT)
- Must not block event processing when delivering notifications

### Business Constraints
- Email delivery uses existing transactional email service (to be determined)
- Storage quota for notifications per user (e.g., 1000 most recent)
- Rate limits to prevent abuse

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| WebSocket connection failures prevent real-time delivery | Medium | High | Notifications persist in database; WebSocket is enhancement, not requirement |
| High notification volume causes performance issues | Medium | Medium | Implement rate limiting, batching, and async delivery |
| Users overwhelmed by notifications | High | High | Smart defaults, user preferences, aggregation |
| Email delivery failures | Low | Medium | Retry logic with exponential backoff; fail gracefully |
| Database growth from notification storage | Medium | Low | Automatic cleanup of old read notifications |

## Dependencies

- **WebSocket Infrastructure**: Existing `/api/v1/ws/events` endpoint
- **EventBusService**: Must publish events for notification triggers
- **Authentication Service**: Must validate user sessions for WebSocket
- **Email Service**: Need to select/configure transactional email provider
- **Frontend Components**: Need notification center UI component

## Open Questions

- [ ] Which email service should we use? (SendGrid, AWS SES, Mailgun, Supabase email?)
- [ ] What should the default notification preferences be for each type?
- [ ] Should notifications be soft-deleted or permanently removed after cleanup?
- [ ] Should we track notification delivery receipts for debugging?
