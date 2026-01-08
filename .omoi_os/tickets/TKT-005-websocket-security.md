---
id: TKT-005
title: WebSocket Authentication and Security
status: backlog
priority: CRITICAL
estimate: M
created: 2026-01-08
updated: 2026-01-08
design_ref: designs/websocket-infrastructure.md
requirements:
  - REQ-WEBSOCKET-FUNC-009
  - REQ-WEBSOCKET-SEC-001
  - REQ-WEBSOCKET-SEC-002
  - REQ-WEBSOCKET-SEC-003
dependencies:
  blocked_by:
    - TKT-003
  blocks: []
---

# TKT-005: WebSocket Authentication and Security

## Description

Implement JWT-based authentication, user authorization, input validation, and connection rate limiting for WebSocket endpoints. This ensures secure access control and prevents abuse.

## Scope

### In Scope
- JWT token validation on WebSocket connection
- User permission verification for agent/task access
- Input validation (message size, filter parameters)
- Per-IP and per-user connection rate limiting
- Audit logging for connection events

### Out of Scope
- WebSocket subprotocol versioning (future consideration)
- Advanced DDoS mitigation beyond rate limiting

## Acceptance Criteria

- [ ] JWT tokens are validated via query parameter `?token={jwt}`
- [ ] Invalid/expired tokens result in 401 connection rejection
- [ ] User permissions are checked for agent/task access
- [ ] Message size is limited to 1 MB per frame
- [ ] Filter parameters are validated (max 50 IDs)
- [ ] Per-IP limit: 10 connections per minute
- [ ] Per-user limit: 5 concurrent connections
- [ ] All connection events are logged (user, IP, timestamp)
- [ ] Security tests verify authentication bypass prevention
- [ ] Rate limiting tests verify enforcement

## Technical Notes

Authentication flow:
1. Client includes JWT in `?token={jwt}` query parameter
2. Server validates token with Supabase auth
3. User ID is extracted and stored in connection state
4. Permission checks use existing Row Level Security (RLS) from database

Rate limiting uses Redis sliding window:
- Key pattern: `ws:ratelimit:ip:{ip}` and `ws:ratelimit:user:{user_id}`
- Window: 60 seconds
- Reset after window expires

Files to create/modify:
- `omoi_os/api/websocket/auth.py` - WebSocket authentication middleware
- `omoi_os/api/websocket/ratelimit.py` - Rate limiting implementation
- Update `omoi_os/api/routes/websocket_agents.py` - Apply middleware

## Dependencies

**Blocked By**: TKT-003 (Core Infrastructure)

**Blocks**: None

## Estimate

**Size**: M (3-5 days)

**Rationale**: Authentication and rate limiting are well-defined patterns. Integration with existing Supabase auth and RLS simplifies permission checks.
