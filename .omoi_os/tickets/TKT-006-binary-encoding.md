---
id: TKT-006
title: Binary Message Encoding and Compression
status: backlog
priority: LOW
estimate: M
created: 2026-01-08
updated: 2026-01-08
design_ref: designs/websocket-infrastructure.md
requirements:
  - REQ-WEBSOCKET-FUNC-011
dependencies:
  blocked_by:
    - TKT-003
  blocks: []
---

# TKT-006: Binary Message Encoding and Compression

## Description

Implement MessagePack binary encoding and gzip compression for high-volume WebSocket streams to reduce bandwidth and improve throughput.

## Scope

### In Scope
- MessagePack encoding as opt-in via `encoding=messagepack` query parameter
- Gzip compression for messages > 1KB
- Encoding negotiation during connection handshake
- Fallback to JSON if encoding not supported

### Out of Scope
- Advanced compression algorithms (brotli, zstd)
- Schema generation for MessagePack messages

## Acceptance Criteria

- [ ] MessagePack encoding is opt-in via query parameter
- [ ] Messages are encoded using MessagePack format
- [ ] Schema includes event_type, timestamp, and typed payload
- [ ] Compression (gzip) is applied to messages > 1KB
- [ ] Clients negotiate encoding during handshake
- [ ] Fallback to JSON if encoding is not supported
- [ ] Performance tests show 30%+ size reduction vs JSON
- [ ] Unit tests verify encoding/decoding correctness

## Technical Notes

MessagePack libraries:
- Python: `msgpack` package
- TypeScript: `@msgpack/msgpack` package

Encoding flow:
1. Client specifies `encoding=messagepack` in query parameter
2. Server confirms encoding in connection handshake
3. Messages are encoded using MessagePack
4. Compression is applied if message size > 1KB
5. Binary frames are sent instead of text frames

Compression flow:
1. Message is serialized (JSON or MessagePack)
2. If size > 1KB, apply gzip compression
3. Set appropriate frame opcode (binary for compressed)
4. Include compression flag in message header

Files to create:
- `omoi_os/api/websocket/encoding.py` - MessagePack encoder/decoder
- `omoi_os/api/websocket/compression.py` - Gzip compression wrapper
- Update `omoi_os/api/websocket/connection_manager.py` - Apply encoding

## Dependencies

**Blocked By**: TKT-003 (Core Infrastructure)

**Blocks**: None

## Estimate

**Size**: M (3-4 days)

**Rationale**: MessagePack integration is straightforward with existing libraries. Complexity is in the encoding negotiation and compression logic, which are well-defined patterns.
