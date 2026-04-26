# Working Buffer

> **Active working memory.** This is the WAL target — write here FIRST, respond SECOND.
> Read this at session start to recover context.

**Last Updated:** 2026-04-26 (evening, post-correction)
**Status:** ACTIVE — Phase 1 plan revised after user correction; awaiting go on Task #1

---

## Strategic Decision (locked 2026-04-26)

Adopt `sandbox-agent-sdk` v0.1.5 (`/Users/kevinhill/Coding/Projects/sandbox-agent-python`) as the agent runtime layer inside FastAPI. **No pivot to TS/hono.** Spec state machine, broker, environment versions, billing, auth, and orchestrator-worker stay in Python.

## Phase 1 Scope (revised)

**Replace Modal-chat path only.** Daytona-chat and orchestrator-worker untouched.

| Decision | Choice |
|---|---|
| Agent runtime | sandbox-agent-sdk via `SandboxAgent.start()` |
| Modal provider | Subclass SDK's `modal` provider; add cross-replica `from_id` attach + broker env injection |
| Image build | Bake `sandbox-agent` server **and** opencode into Modal image at build time |
| Streaming | Non-streaming phase 1 — single `session.message` event on completion |
| Persistence | **Adapter over existing `tasks` + `events` tables. NO new tables.** |
| Frontend | Defer entirely (terminal-first rule) |

## CRITICAL CORRECTION (2026-04-26)

I initially planned to add `agent_sessions` + `agent_session_events` migrations. The user correctly called that bloat. omoi_os already has the right schema — `tasks` acts as session record, `events` already supports session-scoped envelopes via `SessionEventEnvelope`. See `feedback_reuse_existing_tables.md` in auto-memory.

## Schema Mapping — SDK → omoi_os existing tables

### `SessionRecord` → `tasks` table

| SDK field | omoi_os storage | Notes |
|---|---|---|
| `id` | `tasks.id` | direct |
| `created_at` | `tasks.created_at` | direct |
| `sandbox_id` | `tasks.sandbox_id` | direct (already a column) |
| `agent` | `tasks.result['agent_session']['agent']` | new JSONB key, no collision |
| `agent_session_id` | `tasks.result['agent_session']['agent_session_id']` | rotates on reconnect — JSONB write is cheap |
| `last_connection_id` | `tasks.result['agent_session']['last_connection_id']` | JSONB |
| `destroyed_at` | `tasks.result['agent_session']['destroyed_at']` (ISO string) | `tasks.completed_at` differs semantically (chat-reply emit, not sandbox teardown) |
| `session_init` / `config_options` / `modes` | `tasks.result['agent_session']['…']` | JSONB |

### `SessionEvent` → `events` table

| SDK field | omoi_os storage | Notes |
|---|---|---|
| `id` | `events.id` | direct |
| `event_index` | `events.seq` | BigInteger, nullable, perfect fit |
| `session_id` | `events.entity_id` (with `entity_type='session'`) | direct |
| `created_at` | `events.timestamp` | direct |
| `sender` | `events.actor` | **MAPPING REQUIRED**: SDK `'client'` ↔ omoi_os `'user:<uuid>'`; SDK `'agent'` ↔ `'agent'` |
| `payload` | `events.payload` | direct |
| `connection_id` | `events.payload['connection_id']` | nest in JSONB |

### No migration needed
- Existing partial composite index `ix_events_entity_seq` on `(entity_id, seq) WHERE seq IS NOT NULL` (migration 070) covers SDK `list_events` queries.
- `tasks.result['agent_session']` is a clean new JSONB namespace; no key collision with the existing `sandbox_agent` sub-object or any other key inventoried in `task.result`.
- Per-session monotonic `seq` already allocated atomically via `pg_advisory_xact_lock` in `SessionEventEnvelope` — but for SDK-managed sessions the SDK allocates `event_index` client-side, so adapter just writes the SDK-supplied index.

## Open boundary decisions (proposed)

1. **Sender mapping**: SDK `'client'` → omoi_os `'user:<owner_user_id>'` (use the omoi_os user who owns the session). SDK `'agent'` → `'agent'`.
2. **`destroyed_at`**: store in `tasks.result['agent_session']['destroyed_at']` (ISO string). Don't reuse `tasks.completed_at` because semantics differ.
3. **`event_type`** column on `events`: use constant `'session.message'` for SDK-emitted events; this matches the existing convention seen in `SessionEventEnvelope`.
4. **Race on `event_index`** across replicas: SDK allocates client-side, so two replicas could collide. Single-replica Railway deployment makes this a non-issue today. Documented as known limitation.

## Phase 1 Workstream — Two Repos

### In `kivo360/sandbox-agent-python` (SDK patch, ship first — Task #1)
- Define `SessionPersistDriver` Protocol in `sandboxagent/persistence.py` (5 async methods mirroring TS contract)
- Add `persistence=` kwarg to `SandboxAgent.connect()`, `SandboxAgent.start()`, `SandboxAgent.__init__`
- Default to `InMemorySessionPersistDriver()` for back-compat
- Tests for injection point
- Bump 0.1.5 → 0.2.0, publish to PyPI

### In `omoi_os` (adoption, blocked on SDK 0.2.0)
- `backend/pyproject.toml`: pin `sandbox-agent-sdk>=0.2.0` (Task #2)
- `backend/omoi_os/services/agent_session_persist.py` — `OmoiOsSessionPersistDriver` ADAPTER over existing `tasks` + `events` tables (Task #4, no migration)
- `backend/omoi_os/services/sa_modal_provider.py` — subclass SDK modal provider with foreign-attach + broker env (Task #5)
- Modify `backend/omoi_os/services/modal_spawner.py:_build_image` — bake sandbox-agent server alongside opencode (Task #6)
- Modify `backend/omoi_os/services/chat_responder.py:_dispatch_to_sandboxed_agent` — collapse to single SDK call (Task #7)
- Delete `backend/omoi_os/services/modal_sandboxed_agent.py` (Task #7)
- Smoke probe + unit tests (Task #8)

### KILLED tasks
- Task #3 (Alembic migration for new tables) — deleted, no migration needed.

## Risks — Resolved 2026-04-26

### 1. ACP protocol versioning — UNRESOLVED (deepwiki has no index for either repo)
Mitigation: pin SDK version, fetch `@agentclientprotocol/sdk` history from npm directly.

### 2. Reconnect semantics — RESOLVED
- SDK does **lazy replay-based restoration**, not state resurrection.
- On stale `lastConnectionId`, SDK re-issues `session/new`, rotates `agent_session_id`, replays last 50 events as prompt prefix.
- Code: `sdks/typescript/src/client.ts:resumeSession`, `server/packages/opencode-adapter/src/lib.rs:maybe_restore_session`.
- **SSE subscriber orphan caveat**: phase-1 non-streaming, so deferred concern.
- Schema implication: `agent_session_id` rotates → JSONB write handles it.

### 3. `SessionPersistDriver` ABC — RESOLVED
- TS interface known: 5 async methods (get_session, list_sessions, update_session, list_events, insert_event), offset cursor, ON CONFLICT(id) DO UPDATE upserts, ordering (created_at ASC, id ASC) and (event_index ASC, id ASC).
- Python SDK has only `InMemorySessionPersistDriver` concrete class with no Protocol — Task #1 fixes this.
- TS reference impls live at `examples/persist-postgres/src/persist.ts` (the `sdks/persist-postgres/src/index.ts` is a stub that throws).

## Files Modified This Session

- `memory/working-buffer.md` — rewritten with corrected plan
- (auto-memory) `feedback_reuse_existing_tables.md` — new
- (auto-memory) `MEMORY.md` index — appended
