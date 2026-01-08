---
id: TKT-004
title: Terminal Output Streaming Endpoint
status: backlog
priority: HIGH
estimate: M
created: 2026-01-08
updated: 2026-01-08
design_ref: designs/websocket-infrastructure.md
requirements:
  - REQ-WEBSOCKET-FUNC-004
dependencies:
  blocked_by:
    - TKT-003
  blocks: []
---

# TKT-004: Terminal Output Streaming Endpoint

## Description

Implement a dedicated WebSocket endpoint `/ws/terminal/{task_id}` for streaming task stdout/stderr output in real-time. This endpoint is optimized for high-volume text streaming with ANSI color preservation and pause/resume control.

## Scope

### In Scope
- `/ws/terminal/{task_id}` WebSocket endpoint
- Task-level authentication and authorization
- Chunked output delivery (max 4KB per message)
- ANSI escape code preservation
- Pause/resume control messages
- Stream completion notification
- Memory-efficient buffering

### Out of Scope
- Binary message encoding (covered in TKT-006)
- Terminal output persistence (ephemeral only)

## Acceptance Criteria

- [ ] `/ws/terminal/{task_id}` endpoint accepts authenticated connections
- [ ] Task access is validated before streaming starts
- [ ] Output is streamed in 4KB chunks to avoid frame size limits
- [ ] ANSI escape codes and color formatting are preserved
- [ ] Clients can pause/resume the stream via control messages
- [ ] Stream terminates automatically when task completes
- [ ] Maximum 1 MB/s throughput per terminal stream
- [ ] Memory usage is bounded (no unbuffered accumulation)
- [ ] Integration tests verify streaming behavior
- [ ] Load tests validate memory efficiency under high output rates

## Technical Notes

The terminal stream subscribes to a Redis Pub/Sub channel (`terminal:output:{task_id}`) where agent workers publish output chunks.

Key design decisions:
1. **Separate endpoint**: Isolates high-volume terminal traffic from agent status events
2. **Chunking**: 4KB chunks balance frame size limits with throughput
3. **Ephemeral**: No persistence to minimize memory usage
4. **Base64 encoding**: Avoids JSON escaping issues with binary/ANSI data

Files to create:
- `omoi_os/api/websocket/terminal_stream.py` - TerminalStreamer class
- `omoi_os/api/routes/websocket_terminal.py` - `/ws/terminal/{task_id}` route

Integration with agent workers:
- Workers publish to `terminal:output:{task_id}` Redis channel
- Each message contains: `{stream: "stdout|stderr", data: bytes, timestamp}`

## Dependencies

**Blocked By**: TKT-003 (Core Infrastructure)

**Blocks**: None

## Estimate

**Size**: M (3-5 days)

**Rationale**: Straightforward WebSocket streaming with Redis Pub/Sub. Complexity is in chunking and pause/resume control, which are well-defined patterns.
