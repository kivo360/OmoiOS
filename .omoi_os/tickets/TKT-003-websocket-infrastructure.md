---
id: TKT-003
title: Scalable WebSocket Infrastructure Core
status: backlog
priority: HIGH
estimate: XL
created: 2026-01-08
updated: 2026-01-08
design_ref: designs/websocket-infrastructure.md
requirements:
  - REQ-WEBSOCKET-FUNC-001
  - REQ-WEBSOCKET-FUNC-002
  - REQ-WEBSOCKET-FUNC-003
  - REQ-WEBSOCKET-FUNC-005
  - REQ-WEBSOCKET-FUNC-006
  - REQ-WEBSOCKET-FUNC-007
  - REQ-WEBSOCKET-FUNC-008
  - REQ-WEBSOCKET-FUNC-010
  - REQ-WEBSOCKET-FUNC-012
dependencies:
  blocked_by: []
  blocks:
    - TKT-004
    - TKT-005
---

# TKT-003: Scalable WebSocket Infrastructure Core

## Description

Build the core scalable WebSocket infrastructure that enables horizontal scaling across multiple API server instances, message persistence for replay, and production-ready connection lifecycle management. This ticket establishes the foundation for real-time AI agent status streaming.

## Scope

### In Scope
- Multi-instance connection state management using Redis
- Message replay system using Redis Streams
- Connection lifecycle (heartbeat, reconnection, graceful shutdown)
- Rate limiting and backpressure handling
- `/ws/agents` endpoint for agent status and progress streaming
- Internal event publishing API for agent workers

### Out of Scope
- Terminal streaming endpoint (covered in TKT-004)
- Binary message encoding (covered in TKT-006)
- Authentication middleware enhancements (covered in TKT-005)

## Acceptance Criteria

- [ ] ScalableConnectionManager supports 10,000+ concurrent connections across multiple instances
- [ ] Connection state is stored in Redis with cross-instance visibility
- [ ] Message replay delivers missed messages on reconnection (5-minute window)
- [ ] Heartbeat mechanism detects and cleans up stale connections
- [ ] Graceful shutdown drains connections without message loss
- [ ] Rate limiting prevents overwhelming clients (100 msg/s per connection)
- [ ] Backpressure handling drops low-priority messages when buffer is full
- [ ] Subscription filters work across multiple instances
- [ ] Unit tests cover all core functionality
- [ ] Integration tests verify Redis Pub/Sub and Streams behavior
- [ ] Load tests validate 10,000 concurrent connections

## Technical Notes

The implementation builds on the existing `WebSocketEventManager` in `/workspace/backend/omoi_os/api/routes/events.py` but adds:

1. **Redis-backed state**: Connections tracked in Redis for cross-instance visibility
2. **Message persistence**: Redis Streams for replay with 5-minute window
3. **Connection lifecycle**: Heartbeat (30s ping), stale detection, graceful drain
4. **Flow control**: Send buffer monitoring, backpressure, priority queue

Key files to create/modify:
- `omoi_os/api/websocket/connection_manager.py` - New ScalableConnectionManager
- `omoi_os/api/websocket/models.py` - Pydantic models for WebSocket messages
- `omoi_os/api/routes/websocket_agents.py` - New `/ws/agents` endpoint
- `omoi_os/api/routes/internal.py` - Add internal event publishing endpoint

## Dependencies

**Blocked By**: None

**Blocks**:
- TKT-004 (Terminal Streaming)
- TKT-005 (Authentication & Security)

## Estimate

**Size**: XL (8-12 days)

**Rationale**: Complex distributed system with Redis integration, connection lifecycle management, and multi-instance coordination. Requires careful testing and load validation.
