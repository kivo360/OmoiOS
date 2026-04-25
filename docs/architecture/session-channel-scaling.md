# Session Channel Scaling — Multi-Replica Multiplayer

**Created**: 2026-04-24
**Status**: Approved
**Purpose**: Documents how the WebSocket multiplayer plane
(`/api/v1/sessions/{id}/ws`) stays consistent across multiple uvicorn
replicas. Companion to spec §07 (multiplayer) and spec §18 Pattern D.

## The problem we solved

Pre-decoupling, `SessionChannelManager` held a process-local `_rooms`
dict (`session_id → list[(websocket, user_id)]`) and broadcast every
event directly to those sockets. Two failures followed:

1. **`cursor.moved` never crossed replicas.** When user A's browser tab
   landed on replica 1 and user B's tab landed on replica 2, replica 1
   received A's cursor frame and fanned out to replica 1's roster only
   — B never saw it.
2. **The event-firehose bridge was `psubscribe("events.*")`** — every
   replica received every session's events, then filtered in Python.
   At scale, Redis pub/sub throughput × replica count became the limit,
   not the actual session traffic.

## The design

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│  ┌──────────┐        ┌──────────┐          ┌──────────┐                │
│  │ User A   │        │ User B   │          │ User C   │                │
│  │ tab-1    │        │ tab-2    │          │ tab-3    │                │
│  └────┬─────┘        └────┬─────┘          └────┬─────┘                │
│       │ WS                │ WS                  │ WS                   │
│  ╔════▼═══════╗     ╔═════▼══════╗       ╔══════▼═════╗                │
│  ║ Replica 1  ║     ║ Replica 2  ║       ║ Replica 3  ║                │
│  ║ _rooms:    ║     ║ _rooms:    ║       ║ _rooms:    ║                │
│  ║  sid1=[A]  ║     ║  sid1=[B]  ║       ║  sid2=[C]  ║                │
│  ╚════╤═══════╝     ╚═════╤══════╝       ╚══════╤═════╝                │
│       │ SUB ch.sid1       │ SUB ch.sid1         │ SUB ch.sid2          │
│       │                   │                     │                      │
│       └─────────┬─────────┘                     │                      │
│                 │                               │                      │
│           ┌─────▼─────────────────────────────────────┐                │
│           │             Redis PubSub                  │                │
│           │  ch.sid1 ←→ (A's and B's replicas)        │                │
│           │  ch.sid2 ←→ (C's replica only)            │                │
│           └───────────────────────────────────────────┘                │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Three changes landed this architecture

1. **`EventBusService.publish_to_session(session_id, payload)`** — new
   method at `backend/omoi_os/services/event_bus.py`. Publishes to
   `ch.{session_id}` instead of the legacy `events.{event_type}`
   firehose. The legacy publish stays in place (dual-publish during a
   deprecation window).
2. **`SessionEventEnvelope.emit()`** dual-publishes every envelope:
   once to the legacy channel, once to `ch.{session_id}`. Existing
   `events.*` consumers are untouched.
3. **`SessionChannelManager`** subscribes per-session (not firehose).
   On first local participant join for a session, the replica adds
   `ch.{session_id}` to its shared `PubSub`; on last leave, it
   unsubscribes. `cursor.moved` frames publish via `publish_to_session`,
   so every replica with a local participant sees them.

### Why not sticky-session on the LB

Sticky-sessions would pin all participants of one session to one
replica, capping WS capacity at one replica's memory and making a
replica crash drop every participant at once. Redis pub/sub keeps the
app layer stateless — any replica can serve any session — at a small
per-event cost (PUB to Redis + SUB fan-out) which dominates only at
>1000 concurrent multiplayer sessions.

### Why `_rooms` is still in-memory

`_rooms` is no longer the source of truth for "who's in session X"
(Redis is). It's a replica-local cache of `(websocket, user_id)` pairs
so that when a frame arrives from Redis, we know which local sockets to
fan out to. It also holds the reference count that decides when to
unsubscribe.

## The SSE path is unchanged

Spec §03's SSE stream (`GET /sessions/{id}/events`) is DB-first: it
replays from the `events` table and then tails the legacy `events.*`
firehose filtering in Python. The WS migration to per-session channels
touches `session_channel.py` only — SSE keeps working without
modification. This was a deliberate decoupling to make the WS change
reviewable in isolation.

## Verification

- **Unit**: `backend/tests/unit/services/test_event_bus_per_session.py`
  (5 tests) covers `publish_to_session` shape, no-op under Redis-down,
  and `SessionChannelManager` per-session subscribe/unsubscribe refcount.
- **Integration** (future): `test_session_channel_multi_replica.py`
  boots two uvicorn workers on 18001/18002 sharing Redis; asserts
  `cursor.moved` from replica 1 is delivered on replica 2 within 500ms.

## Files

- `backend/omoi_os/services/event_bus.py` — `publish_to_session`
- `backend/omoi_os/services/session_event_envelope.py` — dual-publish
- `backend/omoi_os/api/routes/session_channel.py` — per-session
  subscribe + `cursor.moved` routed through Redis
- `.sisyphus/plans/spec-18-alignment.md` — wave plan that landed this
