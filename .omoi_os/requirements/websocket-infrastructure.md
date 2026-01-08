---
id: REQ-WEBSOCKET-001
title: WebSocket Infrastructure Requirements
feature: websocket-infrastructure
created: 2026-01-08
updated: 2026-01-08
status: draft
category: functional
priority: HIGH
prd_ref: docs/prd-websocket-infrastructure.md
design_ref: designs/websocket-infrastructure.md
---

# WebSocket Infrastructure Requirements

## Overview

These requirements define a scalable WebSocket infrastructure for real-time AI agent status updates, task progress streaming, and terminal output. The infrastructure builds upon the existing EventBusService and `/ws/events` endpoint to provide horizontal scaling, message persistence, and optimized streaming.

## Functional Requirements

### REQ-WEBSOCKET-FUNC-001: Scalable Connection Management

**Priority**: CRITICAL
**Category**: Functional

WHEN a client establishes a WebSocket connection, THE SYSTEM SHALL distribute connections across multiple API server instances using Redis-backed connection state.

**Acceptance Criteria**:
- [ ] Connection state is stored in Redis for cross-instance visibility
- [ ] Each connection has a unique connection_id stored in Redis
- [ ] Connection metadata includes user_id, connected_at, last_heartbeat, instance_id
- [ ] Connections are tracked in a Redis hash with TTL-based cleanup
- [ ] Maximum 10,000 concurrent connections per cluster

**Notes**:
- Connection state enables graceful handoff between instances during deployments
- Redis key pattern: `ws:connections:{connection_id}` with 24h TTL

---

### REQ-WEBSOCKET-FUNC-002: Agent Status Streaming

**Priority**: HIGH
**Category**: Functional

WHEN an agent status changes, THE SYSTEM SHALL broadcast the status update to all subscribed clients within 100ms.

**Acceptance Criteria**:
- [ ] Status updates are published to Redis Pub/Sub channel `events:AGENT_STATUS_CHANGED`
- [ ] Subscribed clients receive updates with agent_id, old_status, new_status, timestamp
- [ ] Multiple clients monitoring the same agent receive simultaneous updates
- [ ] Status updates are persisted to Redis Streams for replay (5-minute window)
- [ ] Clients can filter updates by agent_id or project_id

**Notes**:
- Status values: idle, working, stuck, failed, completed, cancelled
- Redis Stream key: `ws:replay:agent_status:{user_id}` with maxlen=1000

---

### REQ-WEBSOCKET-FUNC-003: Progress Update Streaming

**Priority**: HIGH
**Category**: Functional

WHEN a task execution progresses, THE SYSTEM SHALL stream progress updates to subscribed clients with incremental progress values.

**Acceptance Criteria**:
- [ ] Progress updates include current_step, total_steps, progress_percent, message
- [ ] Updates are batched when multiple steps complete within 100ms
- [ ] Progress bars render smoothly without jumpy behavior
- [ ] Estimated time remaining is calculated and included
- [ ] Progress updates are not persisted (ephemeral only)

**Notes**:
- High-frequency progress updates should not be persisted to avoid memory pressure
- Batching reduces message volume during rapid step completions

---

### REQ-WEBSOCKET-FUNC-004: Terminal Output Streaming

**Priority**: HIGH
**Category**: Functional

WHEN an agent executes a task, THE SYSTEM SHALL stream stdout/stderr output to clients in real-time via a dedicated WebSocket endpoint.

**Acceptance Criteria**:
- [ ] Terminal endpoint: `/ws/terminal/{task_id}` with task-level authentication
- [ ] Output is streamed in chunks (max 4KB per message) to avoid frame size limits
- [ ] ANSI escape codes and color formatting are preserved
- [ ] Clients can pause/resume the stream via control messages
- [ ] Stream is terminated when task completes or connection closes
- [ ] Maximum 1 MB/s throughput per terminal stream

**Notes**:
- Terminal output is ephemeral (not persisted) to minimize memory usage
- Use separate endpoint to avoid flooding general event streams

---

### REQ-WEBSOCKET-FUNC-005: Message Replay on Reconnection

**Priority**: HIGH
**Category**: Functional

WHEN a client reconnects within the replay window, THE SYSTEM SHALL deliver missed messages since the last acknowledged sequence number.

**Acceptance Criteria**:
- [ ] Each message has a monotonically increasing sequence_id
- [ ] Clients send last_sequence_id on reconnection
- [ ] Server delivers messages from Redis Streams since last_sequence_id
- [ ] Replay window is 5 minutes (configurable)
- [ ] Messages are delivered in order with at-least-once guarantee
- [ ] Duplicate messages are de-duplicated by sequence_id on client

**Notes**:
- Redis Streams provide built-in sequence IDs and message replay
- 5-minute window balances memory usage with reconnection tolerance

---

### REQ-WEBSOCKET-FUNC-006: Heartbeat and Connection Health

**Priority**: MEDIUM
**Category**: Functional

WHEN a WebSocket connection is established, THE SYSTEM SHALL maintain connection health via bidirectional heartbeat messages.

**Acceptance Criteria**:
- [ ] Server sends ping every 30 seconds
- [ ] Client must respond with pong within 10 seconds
- [ ] Missed pong threshold is 3 consecutive pings
- [ ] Connection is closed after threshold is exceeded
- [ ] Last heartbeat timestamp is updated in Redis
- [ ] Stale connections are cleaned up via background task

**Notes**:
- Heartbeat prevents silent connection drops
- Redis-based tracking enables cross-instance stale connection cleanup

---

### REQ-WEBSOCKET-FUNC-007: Graceful Connection Shutdown

**Priority**: MEDIUM
**Category**: Functional

WHEN an API server instance shuts down, THE SYSTEM SHALL drain existing connections gracefully before closing.

**Acceptance Criteria**:
- [ ] Shutdown signal triggers graceful drain mode
- [ ] New connections are rejected with HTTP 503 during drain
- [ ] Existing connections are notified of impending shutdown
- [ ] Server waits up to 30 seconds for connections to close naturally
- [ ] Remaining connections are force-closed after timeout
- [ ] Connection state is removed from Redis after shutdown

**Notes**:
- Enables zero-downtime deployments when combined with client reconnection
- Drain state is stored in Redis: `ws:instances:{instance_id}:state`

---

### REQ-WEBSOCKET-FUNC-008: Message Rate Limiting

**Priority**: MEDIUM
**Category**: Functional

WHEN messages are delivered to a connection, THE SYSTEM SHALL enforce per-connection and global rate limits to prevent overwhelming clients or servers.

**Acceptance Criteria**:
- [ ] Per-connection limit: 100 messages per second
- [ ] Global limit: 10,000 messages per second across all connections
- [ ] Rate-limited messages are queued with 5-second TTL
- [ ] Exceeded queue capacity results in message drop with warning
- [ ] Rate limits are tracked via Redis sliding window counter
- [ ] High-priority messages (agent failures) bypass limits

**Notes**:
- Prevents runaway streams from overwhelming system
- Priority queue ensures critical messages are always delivered

---

### REQ-WEBSOCKET-FUNC-009: Connection Authentication

**Priority**: CRITICAL
**Category**: Functional

WHEN a client initiates a WebSocket connection, THE SYSTEM SHALL validate authentication via JWT token before accepting the connection.

**Acceptance Criteria**:
- [ ] JWT token is passed via query parameter `?token={jwt}`
- [ ] Token is validated against Supabase auth
- [ ] Connection is rejected (401) if token is invalid or expired
- [ ] Authenticated user_id is stored in connection state
- [ ] Subscription filters are enforced based on user permissions
- [ ] Token refresh is supported via reconnection with new token

**Notes**:
- Query parameter approach simplifies initial handshake
- Future: Consider WebSocket subprotocol authentication

---

### REQ-WEBSOCKET-FUNC-010: Subscription Filtering

**Priority**: MEDIUM
**Category**: Functional

WHEN a client establishes a connection, THE SYSTEM SHALL support filtering messages by agent_id, project_id, or event_type.

**Acceptance Criteria**:
- [ ] Filters are specified via query parameters on connection
- [ ] Supported filters: `agent_ids`, `project_ids`, `event_types`
- [ ] Filters are stored in connection state in Redis
- [ ] Messages are matched against filters before delivery
- [ ] Filters can be updated dynamically via subscription message
- [ ] Invalid filter values result in connection rejection (400)

**Notes**:
- Reduces unnecessary message delivery and client processing
- Filter format: `?agent_ids=uuid1,uuid2&event_types=STATUS_CHANGED,COMPLETED`

---

### REQ-WEBSOCKET-FUNC-011: Binary Message Encoding

**Priority**: LOW
**Category**: Functional

WHEN high-volume streams are active (terminal output, logs), THE SYSTEM SHALL support binary message encoding to reduce payload size.

**Acceptance Criteria**:
- [ ] Binary encoding is opt-in via `encoding=messagepack` query parameter
- [ ] Messages are encoded using MessagePack format
- [ ] Schema includes event_type, timestamp, and typed payload
- [ ] Clients negotiate encoding during connection handshake
- [ ] Fallback to JSON if encoding is not supported
- [ ] Compression (gzip) is applied to messages > 1KB

**Notes**:
- MessagePack provides 30-50% size reduction over JSON
- Compression further reduces bandwidth for text-heavy payloads

---

### REQ-WEBSOCKET-FUNC-012: Backpressure Handling

**Priority**: MEDIUM
**Category**: Functional

WHEN a client cannot keep up with message delivery, THE SYSTEM SHALL detect backpressure and apply flow control.

**Acceptance Criteria**:
- [ ] Send buffer depth is monitored per connection
- [ ] Buffer depth threshold is 100 messages (configurable)
- [ ] When threshold exceeded, non-critical messages are dropped
- [ ] Critical messages (agent failures) are always queued
- [ ] Client is notified of message drops via control message
- [ ] Send buffer is flushed when capacity recovers

**Notes**:
- Prevents server memory exhaustion from slow clients
- Message priority: CRITICAL > HIGH > NORMAL > LOW

---

## Non-Functional Requirements

### REQ-WEBSOCKET-PERF-001: Latency

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL deliver agent status updates with P95 latency < 100ms from event publication to client delivery.

**Metrics**:
- P50 latency: < 50ms
- P95 latency: < 100ms
- P99 latency: < 500ms

---

### REQ-WEBSOCKET-PERF-002: Throughput

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL support 10,000 concurrent WebSocket connections per cluster with 1,000 messages/second throughput.

**Metrics**:
- Concurrent connections: 10,000+
- Messages per second: 10,000+
- Terminal stream throughput: 1 MB/s per stream

---

### REQ-WEBSOCKET-PERF-003: Availability

**Priority**: HIGH
**Category**: Performance

THE SYSTEM SHALL maintain 99.9% uptime for WebSocket connections excluding planned maintenance windows.

**Metrics**:
- Uptime target: 99.9% (43 minutes/month downtime)
- Mean time to recovery (MTTR): < 5 minutes
- Deployment success rate: > 99%

---

### REQ-WEBSOCKET-SEC-001: Authorization

**Priority**: CRITICAL
**Category**: Security

THE SYSTEM SHALL enforce user-level authorization ensuring clients only receive events for agents and projects they have permission to access.

**Requirements**:
- [ ] User permissions are validated on connection
- [ ] Project-level access control is enforced via Supabase RLS
- [ ] Cross-tenant data leakage is prevented
- [ ] Audit logs record connection events (user, IP, timestamp)

---

### REQ-WEBSOCKET-SEC-002: Input Validation

**Priority**: HIGH
**Category**: Security

THE SYSTEM SHALL validate all client messages to prevent injection attacks and resource exhaustion.

**Requirements**:
- [ ] Message size limit: 1 MB max per frame
- [ ] Filter parameter validation (max 50 IDs per filter)
- [ ] Subscription updates are rate-limited (10 per second)
- [ ] Invalid messages result in connection close with error code

---

### REQ-WEBSOCKET-SEC-003: Connection Rate Limiting

**Priority**: MEDIUM
**Category**: Security

THE SYSTEM SHALL limit connection rate per IP and per user to prevent connection storms and DoS attacks.

**Requirements**:
- [ ] Per-IP limit: 10 connections per minute
- [ ] Per-user limit: 5 concurrent connections
- [ ] Exceeded limits return HTTP 429 with retry-after header
- [ ] Rate limits are tracked via Redis sliding window

---

## Traceability

| Requirement ID | PRD Section | Design Section | Ticket |
|----------------|-------------|----------------|--------|
| REQ-WEBSOCKET-FUNC-001 | Horizontal Scaling | Architecture | TKT-003 |
| REQ-WEBSOCKET-FUNC-002 | User Stories #1 | Agent Events | TKT-003 |
| REQ-WEBSOCKET-FUNC-003 | User Stories #3 | Progress Streaming | TKT-003 |
| REQ-WEBSOCKET-FUNC-004 | User Stories #2 | Terminal Streaming | TKT-004 |
| REQ-WEBSOCKET-FUNC-005 | Message Replay | Replay System | TKT-003 |
| REQ-WEBSOCKET-FUNC-006 | Connection Lifecycle | Heartbeat | TKT-003 |
| REQ-WEBSOCKET-FUNC-007 | Graceful Deployments | Shutdown | TKT-003 |
| REQ-WEBSOCKET-FUNC-008 | Rate Limiting | Flow Control | TKT-003 |
| REQ-WEBSOCKET-FUNC-009 | Authentication | Security | TKT-005 |
| REQ-WEBSOCKET-FUNC-010 | Subscription Filters | Filtering | TKT-003 |
| REQ-WEBSOCKET-FUNC-011 | Stream Optimization | Binary Encoding | TKT-006 |
| REQ-WEBSOCKET-FUNC-012 | Backpressure | Flow Control | TKT-003 |
| REQ-WEBSOCKET-PERF-001 | Success Metrics | Performance | All |
| REQ-WEBSOCKET-PERF-002 | Success Metrics | Performance | All |
| REQ-WEBSOCKET-PERF-003 | Success Metrics | Reliability | All |
| REQ-WEBSOCKET-SEC-001 | Security | Authorization | TKT-005 |
| REQ-WEBSOCKET-SEC-002 | Security | Input Validation | TKT-005 |
| REQ-WEBSOCKET-SEC-003 | Security | Rate Limiting | TKT-005 |
