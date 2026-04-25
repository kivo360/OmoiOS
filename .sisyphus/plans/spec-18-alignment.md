# Spec §12–§18 Alignment — SDK Parity + Multiplayer + Gaps

## TL;DR

> **Quick Summary**: The session-ticket decoupling (just shipped) enabled the
> spec §03 body on the SDK-direct path, but a handful of structural gaps
> against docs §12–§18 (and especially §18 — SDK & client patterns) remain.
> Two of them are live regressions introduced by decoupling itself, not
> theoretical gaps: (1) `sessions.list()` can't see ticket-less sessions
> because `tasks_router.list_tasks` INNER JOINs on `tickets`; (2) the
> multiplayer WebSocket plane fragments at >1 replica because `_rooms` is
> process-local and `cursor.moved` bypasses Redis. Five other gaps are
> structural alignment with spec §18 (missing `connections` + `usage`
> resources on the SDK surface, `telemetry` callback, `AbortSignal`
> propagation) or spec §17 adapter work (`EnvironmentVersion.exposed_ports` +
> `persistent_volume` declarations — on versions, not parents, to respect
> spec §05 immutability; hostname-level egress proxy verification).
>
> **Deliverables**:
> - Fix `sessions.list()` to surface ticket-less sessions (workspace-scoped
>   query, not ticket-joined)
> - Per-session Redis channel (`events.{session_id}` + `ch.{session_id}`)
>   replacing the firehose psubscribe + process-local `_rooms`
> - `cursor.moved` routes through Redis so multi-replica frontends see each
>   other's cursors
> - `connections` SDK resource (list/remove user-linked OAuth providers) +
>   backing `/api/v1/connections/*` routes
> - `usage` SDK resource (thin wrapper over existing `/api/v1/billing/usage`)
> - `telemetry` callback on both SDKs (five events: request, response,
>   stream_open, stream_close, error)
> - `AbortSignal` / `anyio.CancelScope` propagation audit + fix on any
>   iterators that don't honour it today
> - `EnvironmentVersion.exposed_ports` + `persistent_volume` columns
>   (migration 072, on `environment_versions` — matches the pattern set by
>   `credentials` + `egress` so spec §05 per-version immutability holds)
>   for hosted-editor + workspace-persistent volume support
> - Hostname-level egress proxy conformance test (we have the flag; prove it
>   blocks `api.evil.com` and allows `api.anthropic.com`)
> - `SessionResponse` includes `urls.{events_sse, websocket, editor}` +
>   `usage.{compute_seconds, tokens_input, tokens_output}` per spec §02
>
> **Estimated Effort**: Medium (~4–5 working days)
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: Wave 1 (live regressions) → Wave 2 (surface completeness)
> → Wave 3 (env v1.1 + egress) → Wave 4 (SDK polish + tests)

---

## Context

### Why now

We just landed `session-ticket-decoupling.md`. Spec §18 §1 says the SDK's
job is to make every client runtime "look the same from the outside" via
four primitive patterns (fire-and-forget, sync-wait, live-stream,
multiplayer). Patterns A/B/C work end-to-end post-decoupling. Pattern D
(multiplayer) technically works against a single-replica backend but will
silently fragment in production. Separately, two live regressions slipped
through decoupling — found by reading §18 against the current code — that
need to be fixed before customers start creating ticket-less sessions.

### Discovery findings (grep + read, verified 2026-04-24)

**Live regressions from the decoupling (must fix):**

- `backend/omoi_os/api/routes/tasks.py:485-497` — `list_tasks` short-circuits
  to `return []` when `accessible_project_ids` is empty (line 488), then
  does `.join(Ticket, Task.ticket_id == Ticket.id)` at line 495 as an inner
  join. A user who's only created ticket-less sessions will see an empty
  list on `GET /api/v1/sessions`. This is the single biggest hole because
  `sessions.py:list_sessions` delegates to `tasks_router.list_tasks`.
- `backend/omoi_os/api/routes/sessions.py:262, 303, 352, 457` — four
  delegations to `tasks_router.*` still force ticket-chain semantics onto
  the session surface. The create path was fixed; list/get/cancel/update
  still route through ticket-aware handlers. Get and cancel happen to work
  (they key on task_id and don't filter) but the coupling isn't intentional
  — it's accidental surface-sharing.

**Spec §18 §2 "Core surface" gaps (canonical 7 resources):**

- Python SDK (`sdk/python/omoios/client.py:206-215`) exposes 6 resources:
  `sessions, credentials, environments, artifacts, webhooks, workspaces`.
  Spec §18 §2 defines 7: `sessions, environments, secrets, connections,
  webhooks, usage, artifacts`. Mapping: our `credentials` == spec's
  `secrets` (semantic match). Missing: **`connections`** (user-linked OAuth
  providers — personal GitHub/GitLab/Linear) and **`usage`** (per-org
  compute-seconds + token counts).
- TypeScript SDK mirrors Python — same two resources missing.
- Backend: `billing.py:1505, 1557` already has `get_usage` + `get_usage_summary`
  — the `usage` SDK resource is a thin wrapper, not new backend work. User
  OAuth token storage exists in `user.attributes['github_access_token']`
  and the broker Model-A path already reads it — the `connections` routes
  need to be added but the underlying data model is there.

**Spec §18 §1 "five things" SDK principles (discipline gaps):**

- **Cancellation propagation** (principle 5). Python SDK `sessions.events()`
  accepts no explicit cancel token; aborts rely on the caller `break`-ing
  the `async for` loop, which is correct for iter semantics but doesn't
  cancel the inbound `httpx_sse` request on a `CancelScope` boundary.
  Callers who wrap in `asyncio.wait_for` get partial aborts. TS side takes
  `signal: AbortSignal` in `events({signal})` per our earlier implementation
  — verify it propagates to the underlying `fetch` POST on create/reply as
  well.
- **Telemetry hook** (spec §18 §2 constructor option `telemetry: (e) => void`).
  Neither SDK exposes this. Spec §18 §7 non-goals explicitly says retries
  and caching are the *client's* responsibility — but telemetry is a first-
  class option because you can't build retries/caching without it.

**Spec §07 + §18 Pattern D multiplayer seams:**

- `backend/omoi_os/api/routes/session_channel.py:49` — `_rooms:
  dict[session_id, list[(ws, user_id)]]` is a process-local dict. Two
  frontend tabs hitting different uvicorn replicas see disjoint rosters.
- `session_channel.py:163, 292` — `cursor.moved` calls `sock.send_json()`
  directly, fanning out only within the single replica's `_rooms`. Matches
  spec §07 (cursor.moved is ephemeral, no DB store) but must still cross
  replicas via Redis pub/sub or the spec §18 Pattern D is broken under HA.
- `session_channel.py:129-160` — `_bridge_loop` psubscribes to
  `events.*` (the entire firehose). At scale every uvicorn replica receives
  every session's events, then filters in Python. Replace with per-session
  channel names so Redis does the filtering.

**Spec §02 §Session response-shape gaps:**

- `SessionResponse` (in `sessions.py`) doesn't carry `urls.events_sse /
  websocket / editor` or `usage.{compute_seconds, tokens_input,
  tokens_output}`. Spec §02 §Session lists these as first-class fields;
  spec §15 §11 explicitly calls out `exposed_ports` and `persistent_volume`
  as required for hosted-editor support via Modal/Daytona tunnels. They
  belong on `environment_versions` alongside the already-versioned
  `credentials` + `egress` fields so spec §05 immutability is preserved.

**Spec §17 §3 explicit adapter gaps still open:**

- `EnvironmentVersion.exposed_ports: number[]` column — not present.
  Needed for hosted-editor iframe pattern (spec §18 §11 client pattern).
  Lands on `environment_versions`, not `environments`, so it's frozen per
  version alongside `credentials` + `egress` per spec §05 immutability.
- `EnvironmentVersion.persistent_volume: bool` — not present. Same
  location rationale. `volume_name` is derived from `workspace_id` at
  spawn, not stored as a column (spec §15 §4 #3).
- Hostname-level egress: agent-platform-gaps wired `egress_proxy_enabled`
  feature flag and `HTTP_PROXY/HTTPS_PROXY` env injection; we haven't
  proved that `api.evil.com` is actually blocked with a conformance test
  against the flag. Spec §17 §3 #5 and §15 §6 are emphatic that CIDR
  allowlist is not sufficient.

### Metis Review

**Architectural trade-offs considered:**

1. **Fix `list_tasks` in-place vs. give `sessions.py` its own list query.**
   In-place is tempting (one-line change: swap INNER JOIN for OUTER JOIN,
   widen the accessible check to `(project_ids) OR workspace_id IN user_orgs
   OR created_by == user.id`). But `tasks_router.list_tasks` is also called
   by the dashboard's Kanban board, which *intentionally* excludes
   ticket-less sessions (they have no phase column). **Decision**: give
   `sessions.py:list_sessions` its own query shape — multi-tenancy via the
   `verify_task_access` precedence chain from the prior plan — and leave
   `tasks_router.list_tasks` untouched. Same pattern as the `create_session`
   split (legacy delegates vs SDK-direct direct-insert).

2. **Per-session Redis channel vs. keep psubscribe + replica filtering.**
   Per-session channels scale with the number of active sessions (say 10k),
   each a cheap Redis key. Psubscribe on `events.*` scales with the number
   of *replicas* (single-digit) but every replica receives every event —
   Redis pub/sub is O(subscribers × events), so per-session wins at the
   replica count we'd actually run (≥3). **Decision**: migrate to
   `events.{session_id}` + `ch.{session_id}` naming, one subscription per
   active WS session on the replica that holds it, unsubscribe on
   disconnect. Same pattern OpenAI's Realtime API uses.

3. **Move `cursor.moved` through Redis, or sticky-session at the LB.**
   Sticky-sessions are operationally simpler (one line in the LB config)
   but force all participants of one session onto one replica — meaning a
   session's WS capacity is capped at one replica's memory, and a replica
   crash drops every participant simultaneously. Redis-pub-sub is stateless
   at the app level: any replica can serve any session. **Decision**:
   Redis pub/sub for `cursor.moved`. The throughput overhead (one Redis
   PUB per cursor event × N replicas' SUB) is tiny — cursor events are
   ≤20/sec/user and the payload is ~60 bytes. Sticky-sessions remain a
   valid fallback if Redis turns into a hot spot, but we won't need it
   until >1000 concurrent multiplayer sessions.

4. **`connections` SDK resource: thin wrapper vs. full Better Auth `account`
   read-through.** Spec §17 §6 says don't adopt Better Auth for omoi_os.
   We store user OAuth tokens in `user.attributes['github_access_token']`
   today. The clean model for `connections` is: a list endpoint that
   reflects which providers the user has connected + when, and a DELETE
   endpoint that wipes the stored token. No token minting — that's the
   broker's job. **Decision**: thin wrapper. `GET /api/v1/connections` →
   `[{provider: "github", connected_at, scopes}]`. `DELETE
   /api/v1/connections/{provider}` → wipes the attribute key.

5. **Where do `exposed_ports` + `persistent_volume` live: `environments`
   or `environment_versions`?** Spec §05 (and our existing schema) says
   environments are immutable per version — `credentials` and `egress`
   already live on `EnvironmentVersion`. Putting `exposed_ports` on the
   parent `environments` table would let a tenant mutate in place and
   retroactively change what every in-flight session's sandbox exposes,
   which is the exact failure mode §05 was written to prevent. **Decision**:
   both columns go on `EnvironmentVersion`, matching the pattern already
   set by `credentials` and `egress`. `volume_name` is dropped entirely
   from the column set — per spec §15 §4 #3 the volume is workspace-scoped,
   so the spawner derives `f"ws-{workspace_id}"` at runtime. An environment
   version says "I want a volume mounted"; the session's workspace decides
   which one. This also means changing `persistent_volume` is a new-version
   operation, forcing intentional opt-in rather than a silent flip.

6. **Ship migration 072 now vs. wait for first customer request.** The spec
   §15 §11 argument to ship now still holds: additive and reversible,
   `persistent_volume` is surprising to retrofit, hosted-editor is the
   demo piece that sells the product per spec §12 Phase 5. **Decision**:
   ship. Spawner gets a guard: if `env_version.exposed_ports` is empty, no
   tunnel is minted (backwards compatible). If set and Daytona/Modal
   supports tunnels, URLs surface on `Session.urls.editor`.

**Risks logged:**

- **Per-session Redis subscription churn under rapid session creation.** A
  burst of 1000 sessions in 1s = 1000 `subscribe()` calls. Redis can
  absorb this but the Python client's pubsub loop is single-threaded per
  connection. ✅ Mitigated: one `PubSub` object per replica multiplexes
  all session subscriptions via `subscribe(*channels)` — no N-connection
  explosion. Tested with `pubsub.subscribe(f"events.{sid}" for sid in
  1000 sessions)` — single round-trip.
- **`cursor.moved` fan-out cost on 100-participant sessions.** Spec §07
  explicitly says cursor events are ephemeral and high-frequency. ✅
  Mitigated: `cursor.moved` publishes to `ch.{session_id}` on Redis; only
  replicas holding ≥1 participant for that session are subscribed. Cost
  scales with `participants × events/sec`, not with total sessions.
- **Ticket-less `list_tasks` changes leak into the dashboard's Kanban
  board.** ✅ Mitigated: we don't touch `tasks_router.list_tasks`. The new
  `list_sessions` query in `sessions.py` is a parallel code path.
- **`GET /api/v1/connections/{provider}` exposes whether a user has a
  token for a provider — low-info-leak but non-zero.** ✅ Mitigated: route
  is behind `get_current_user` (user-scoped, not platform-key-scoped).
  Platform keys can't enumerate a user's connections.
- **`exposed_ports` on existing environment *versions* default to empty, so
  existing sandboxes don't change behavior. Tunnel URLs only appear when
  a tenant opts in by rolling a new version with the field set.** ✅ Verified
  in spec §15 §11. Note: this means older versions of an environment stay
  port-less forever — the caller explicitly cuts a new version when they
  want hosted-editor. That matches spec §05's "pin at create" semantics.

---

## Work Objectives

### Core Objective
Close the gap between what we ship and what spec §18 requires for a
platform SDK that "makes every client runtime look the same" — fix the two
live regressions from decoupling, fill the canonical 7-resource SDK
surface, make Pattern D multiplayer actually survive at >1 replica, and
land the two small Environment columns that spec §15 §11 lists as required
for hosted-editor support.

### Concrete Deliverables
- `backend/omoi_os/api/routes/sessions.py` — new `_list_sessions_query()`
  helper with workspace-scoped + ACL-scoped + created_by-scoped access
  filter; `list_sessions` no longer delegates to `tasks_router.list_tasks`
- `backend/omoi_os/api/routes/session_channel.py` — per-session Redis
  pub/sub (`events.{session_id}` + `ch.{session_id}`); `cursor.moved`
  routed through Redis; `_rooms` becomes a cache for which replica holds
  each participant, not the source of truth
- `backend/omoi_os/services/event_bus.py` — `publish_to_session(session_id,
  envelope)` → `events.{session_id}` + legacy `events.{entity_id}` (parallel
  publish for one deprecation window)
- `backend/omoi_os/api/routes/connections.py` — new module, 3 routes:
  `GET /api/v1/connections`, `DELETE /api/v1/connections/{provider}`,
  `POST /api/v1/connections/{provider}/start` (kicks off OAuth flow for
  SDK callers who don't have dashboard access)
- `backend/omoi_os/api/routes/usage.py` — new module, 2 routes: `GET
  /api/v1/usage` (current billing period summary), `GET
  /api/v1/usage/sessions/{id}` (per-session breakdown)
- `backend/migrations/versions/072_environment_version_ports_and_volume.py`
  — adds columns on `environment_versions` (NOT `environments`, to preserve
  spec §05 immutability — every version freezes its ports + volume
  declaration the same way `credentials` and `egress` already are):
  `environment_versions.exposed_ports JSONB`,
  `environment_versions.persistent_volume BOOLEAN DEFAULT false`.
  `volume_name` is NOT stored here — the volume is workspace-scoped per
  spec §15 §4 #3 ("Volumes scoped to `workspace_id`, not `session_id`"),
  so the spawner synthesises `f"ws-{workspace_id}"` at runtime. An
  environment version only declares *whether* it wants a volume mounted;
  *which* volume comes from the session's workspace.
- `backend/omoi_os/models/environment.py` — mirror the new columns on
  `EnvironmentVersion` (not `Environment`)
- `backend/omoi_os/services/daytona_spawner.py` — narrow touch: if
  `env.exposed_ports` non-empty, open tunnels for each port and write the
  first one to `session.urls.editor` via `Session` response shape; if
  `env.persistent_volume`, mount at `/workspace`
- `backend/omoi_os/api/routes/sessions.py` — `SessionResponse` now
  populates `urls.events_sse`, `urls.websocket`, `urls.editor`, and
  `usage.{compute_seconds, tokens_input, tokens_output}` (the latter
  resolved from `cost_records` aggregation already in the DB)
- `backend/tests/integration/test_egress_conformance.py` — conformance test
  that spawns a sandbox with `allowed_hosts=['api.anthropic.com']` and
  asserts curl to `api.evil.com` returns 403 from the proxy while
  `api.anthropic.com` returns a connection (spec §17 §3 #5)
- Python SDK additions:
  - `sdk/python/omoios/resources/connections.py` (new)
  - `sdk/python/omoios/resources/usage.py` (new)
  - `sdk/python/omoios/client.py` — wire both into `AsyncOmoiOSClient`
  - Constructor `telemetry: Optional[Callable[[TelemetryEvent], None]] = None`
    kwarg; emitted on each `_request` call with `(method, path, status,
    duration_ms, error?)` + stream open/close
  - `sdk/python/omoios/resources/sessions.py` — `events()` accepts
    `cancel_scope: Optional[anyio.CancelScope] = None`; propagates to
    `aconnect_sse`
- TypeScript SDK additions:
  - `sdk/typescript/src/resources/connections.ts` (new)
  - `sdk/typescript/src/resources/usage.ts` (new)
  - `sdk/typescript/src/client.ts` — wire in; `telemetry` option on
    constructor; `AbortSignal` propagation verified on every method that
    makes a request
  - `sdk/typescript/src/resources/sessions.ts` — `create()` and `reply()`
    accept `signal: AbortSignal` to match `events()`
- Docs:
  - `docs/architecture/session-channel-scaling.md` — explains the
    per-session Redis channel model with an ASCII sequence diagram

### Definition of Done
- [ ] `alembic upgrade head` + `alembic downgrade -1` clean for 072
- [ ] Ticket-less sessions appear in `GET /api/v1/sessions` for their
      creator (test asserts list length ≥ 1 after create)
- [ ] Multi-replica integration test: start two uvicorn workers bound to
      the same Redis; open a WS on replica A and another on replica B for
      the same session; user A sends `cursor.moved`; user B receives it
- [ ] Smoke test `session_channel_multi_replica` PASSes
- [ ] `client.connections.list()` returns connected providers for the
      current user
- [ ] `client.usage.current()` returns current-period compute/token totals
- [ ] `telemetry` callback receives ≥1 event per method call in both SDKs
- [ ] `pnpm test` + `uv run pytest sdk/python/tests/` green
- [ ] `SessionResponse` JSON includes `urls` and `usage` objects
- [ ] Egress conformance test: `api.evil.com` blocked, `api.anthropic.com`
      allowed, evidence saved
- [ ] OpenAPI diff shows `connections`, `usage`, `urls`, `usage` additions

### Must Have
- Ticket-less sessions visible via `sessions.list()` filtered by the
  caller (workspace org OR ACL OR created_by)
- Cursor events cross replica boundaries via Redis
- Per-session Redis channel replaces the `events.*` firehose
- `connections` + `usage` SDK resources in both Python and TypeScript
- `telemetry` callback (both SDKs)
- `EnvironmentVersion` columns `exposed_ports`, `persistent_volume`
  (volume_name is derived from `workspace_id` at spawn time, not stored)
- `Session.urls.{events_sse, websocket, editor}` populated on GET/create
- `Session.usage.{compute_seconds, tokens_input, tokens_output}` from
  `cost_records` aggregation
- Egress conformance test (passes = blocks `api.evil.com`, allows
  `api.anthropic.com`)

### Must NOT Have (Guardrails)
- Do **not** touch `tasks_router.list_tasks` — the Kanban board depends on
  its ticket-joined semantics
- Do **not** introduce a new WebSocket library — keep `fastapi.WebSocket`
  + Redis pub/sub
- Do **not** add sticky-session LB config to fix multiplayer; use Redis
- Do **not** invent new credential storage for `connections` — reflect
  `user.attributes` + broker state
- Do **not** build an OAuth server in SDK — `connections.start()` returns
  a platform URL for the user to visit; SDK never handles the callback
- Do **not** touch spec §13 Better Auth for omoi_os (spec §17 §6 explicitly
  advises against it)
- Do **not** rewrite `daytona_spawner.py` — the exposed-ports + volume
  wiring are ≤30 LOC adds
- Do **not** ship `EnvironmentVersion.image.kind="registry"` — that's for
  Modal integration in a later plan; exposed_ports + volume stand alone
- Do **not** add `telemetry` as a required kwarg — optional + default None
- Do **not** break the legacy `events.{entity_id}` publish path — dual-
  publish during the transition window, remove legacy in a follow-up plan

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — all verification is agent-executed.
> Evidence saved to `.sisyphus/evidence/spec-18-alignment/task-{N}-*`.

### Test Decision
- **Framework**: pytest + vitest + multi-replica uvicorn harness
- **TDD**: RED → GREEN → REFACTOR per task
- **Integration surface**: real Postgres + real Redis (Docker) for multi-
  replica tests; mocked httpx for SDK unit tests; real backend for SDK e2e

### QA Policy
- **List regression**: pytest — create 1 ticket-less session as user A,
  list sessions, assert length ≥ 1 and id matches
- **Multi-replica multiplayer**: spawn two uvicorn workers on different
  ports sharing one Redis; open WS on each; verify both receive each
  other's `cursor.moved`; save transcript
- **Per-session channel**: assert with `redis-cli PUBSUB CHANNELS` that
  `events.{session_id}` shows up on subscribe, disappears on WS close
- **Connections SDK**: mock the backend — `client.connections.list()`
  returns `[{provider: 'github', connected_at, scopes}]`
- **Usage SDK**: mock — `client.usage.current()` returns
  `{compute_seconds, tokens_input, tokens_output, period_start, period_end}`
- **Telemetry**: create session via SDK with a capturing `telemetry`
  callback; assert ≥1 event received with shape `(kind, method, path,
  duration_ms)`
- **AbortSignal (TS)**: call `client.sessions.create({..., signal})` with
  an already-aborted signal; assert `AbortError` raised within 50ms
- **CancelScope (Python)**: wrap `events()` iteration in
  `asyncio.wait_for(..., timeout=0.1)`; assert underlying `httpx_sse`
  connection closes (no zombie tcp) via `client._http` inspection
- **`urls.editor`**: spawn a Daytona sandbox with `exposed_ports=[8443]`;
  assert `SessionResponse.urls.editor` contains a `https://` URL
- **Persistent volume**: create environment with `persistent_volume=true`;
  spawn session; write to `/workspace/foo`; spawn second session in same
  workspace; assert `/workspace/foo` exists
- **Egress conformance**: spawn sandbox with `allowed_hosts=['api.anthropic.com']`;
  `curl http://api.evil.com` → non-200 (blocked by proxy); `curl
  https://api.anthropic.com/v1/messages` → 401 (reached API, no auth
  header) = proof the host was allowed; save both curl outputs

---

## Execution Strategy

### Wave Structure

```
Wave 1 — Live regressions [sequential — the two bugs that must ship before
                           new ticket-less users hit them]
  ├─ Task 1: list_sessions own-query
  └─ Task 2: Per-session Redis channel + cursor.moved cross-replica

Wave 2 — Surface completeness [parallel, gated by Wave 1]
  ├─ Task 3: connections backend + SDK (Python + TS)
  ├─ Task 4: usage backend wrapper + SDK (Python + TS)
  └─ Task 5: SessionResponse urls + usage fields

Wave 3 — Environment v1.1 + egress proof [parallel, gated by Wave 2]
  ├─ Task 6: Migration 072 (exposed_ports, persistent_volume, volume_name)
  ├─ Task 7: Spawner wiring for tunnels + volume
  └─ Task 8: Egress conformance test

Wave 4 — SDK polish [parallel, gated by Wave 2]
  ├─ Task 9: Telemetry callback (both SDKs)
  ├─ Task 10: AbortSignal / CancelScope audit + fixes
  └─ Task 11: Docs — session-channel-scaling.md + SDK README refresh

Final Verification Wave
  ├─ F1: Multi-replica multiplayer integration suite
  ├─ F2: Smoke test all existing phases + new ones
  └─ F3: OpenAPI diff + SDK method-count parity check
```

### Dependency Matrix

| Task | Depends on | Blocks |
|------|-----------|--------|
| 1    | —         | F1, F2 |
| 2    | —         | F1 |
| 3    | 1         | 11, F3 |
| 4    | 1         | 11, F3 |
| 5    | 1, 4      | F2, F3 |
| 6    | —         | 7 |
| 7    | 6         | F2 |
| 8    | —         | F2 |
| 9    | 3, 4      | F2 |
| 10   | —         | F2 |
| 11   | 2, 3, 4, 9 | F3 |

---

## TODOs

### Wave 1 — Live regressions

#### Task 1 — `list_sessions` own query (decouple from tasks_router.list_tasks)
**Files**: `backend/omoi_os/api/routes/sessions.py`
**What**: New helper `_list_sessions_query(current_user, db, filters)` that
LEFT JOINs Ticket (not INNER), and builds a WHERE clause that admits:
- tasks where `task.ticket_id` resolves to a project in user's orgs (legacy), OR
- tasks where `task.workspace_id` resolves to a workspace in user's orgs, OR
- tasks where `task.created_by == current_user.id`, OR
- tasks with a `SessionACL` grant for `current_user.id`

Replace the `await tasks_router.list_tasks(...)` call with the new query.
Preserve the existing filter params (`status`, `phase_id`, `has_sandbox`,
`ticket_id`, `limit`) + add `workspace_id` filter.

**QA**: pytest integration — create ticket-less session, list via SDK,
assert visibility. Cross-org negative test: user B in org Y should NOT
see user A's ticket-less session.
**Must not**: Don't touch `tasks_router.list_tasks`. Don't change the
response shape (`_add_session_id_to_response` still wraps each dict).

#### Task 2 — Per-session Redis channel + cursor.moved cross-replica
**Files**: `backend/omoi_os/api/routes/session_channel.py`,
`backend/omoi_os/services/event_bus.py`,
`backend/omoi_os/services/session_event_envelope.py`
**What**:
- Rename publish path: `SessionEventEnvelope.emit` now publishes to
  `events.{session_id}` (primary) AND `events.{entity_id}` (legacy, one
  release window)
- `SessionChannelManager.register(ws, session_id, user_id)` subscribes to
  `events.{session_id}` + `ch.{session_id}` on first participant; refcounts
  by `len(_rooms[sid])`; unsubscribes when roster hits 0
- New `_ephemeral_bridge_loop` handles the ephemeral `ch.{session_id}` Redis
  channel for `cursor.moved` + future presence frames
- `cursor.moved` send path: when a participant sends `cursor.moved`, the
  server PUBLISHes to `ch.{session_id}` with `{from_user_id, payload}`;
  every replica holding subscribers for that session rebroadcasts to its
  local WS clients (excluding the sender)
- Remove the `psubscribe("events.*")` call — replaced by per-session
  subscribes

**QA**: Integration test — boot 2 uvicorn processes on ports 18001 + 18002
sharing one Redis; open WS client A → 18001, WS client B → 18002, same
session; A sends `cursor.moved`, assert B receives within 500ms. Save WS
frame transcripts to evidence.
**Must not**: Don't break the SSE replay path — SSE is DB-first, uses
`events` table. WebSocket is Redis-first.

### Wave 2 — Surface completeness

#### Task 3 — `connections` backend + SDK
**Files**: `backend/omoi_os/api/routes/connections.py` (new),
`sdk/python/omoios/resources/connections.py` (new),
`sdk/typescript/src/resources/connections.ts` (new), client wiring
**What**:
```
GET    /api/v1/connections              → list connected providers for user
DELETE /api/v1/connections/{provider}   → revoke (wipe stored token)
POST   /api/v1/connections/{provider}/start → returns {oauth_start_url}
```
Reflect storage in `user.attributes` (github_access_token, etc.). The
`start` route builds the existing GitHub OAuth URL + signs a state param
with user_id; the callback is the existing dashboard handler.

SDK: `client.connections.list() -> List[Connection]`,
`client.connections.remove(provider)`, `client.connections.oauth_url(provider)`.

**QA**: Mock backend — SDK unit test asserts wire format. Live backend —
curl + assert shape. Save evidence.
**Must not**: Don't try to mint tokens — broker's job. Don't expose raw
access tokens in the list response (return `{provider, connected_at,
scopes, expires_at}` only).

#### Task 4 — `usage` backend wrapper + SDK
**Files**: `backend/omoi_os/api/routes/usage.py` (new),
`sdk/python/omoios/resources/usage.py` (new),
`sdk/typescript/src/resources/usage.ts` (new)
**What**:
```
GET /api/v1/usage                       → current-period summary
GET /api/v1/usage/sessions/{id}         → per-session breakdown
```
Backend: thin wrapper over `billing.get_usage` (line 1505) + new
`cost_records` aggregation by task_id. SDK: `client.usage.current()`,
`client.usage.for_session(session_id)`.

**QA**: SDK unit + e2e. Save evidence.
**Must not**: Don't dual-publish with `/api/v1/billing/usage` — route
`/api/v1/usage` to the same handler.

#### Task 5 — `SessionResponse.urls` + `SessionResponse.usage`
**Files**: `backend/omoi_os/api/routes/sessions.py`
**What**: On GET `/api/v1/sessions/{id}`, populate:
- `urls.events_sse = f"{base}/api/v1/sessions/{id}/events"`
- `urls.websocket  = f"{ws_base}/api/v1/sessions/{id}/ws"`
- `urls.editor     = session_editor_url_or_none(task)` — resolves to the
  Daytona/Modal tunnel URL from `task.sandbox_id` if `env.exposed_ports`
  is non-empty
- `usage.compute_seconds = sum(cost_records.compute_seconds)`
- `usage.tokens_input    = sum(cost_records.tokens_input)`
- `usage.tokens_output   = sum(cost_records.tokens_output)`

**QA**: curl `GET /sessions/{id}` after create → assert `urls` + `usage`
present. Save sample response.
**Must not**: Don't compute the aggregation in-request synchronously for
every session — cache via a materialized view or short-TTL Redis.

### Wave 3 — Environment v1.1 + egress proof

#### Task 6 — Migration 072: environment_versions exposed_ports + volume
**Files**: `backend/migrations/versions/072_environment_version_ports_and_volume.py`
**What**:
```python
# Land on environment_versions (not environments) to respect spec §05
# immutability — sessions pin a version at create, and the port/volume
# declaration is frozen alongside `credentials` and `egress`.
op.add_column(
    "environment_versions",
    sa.Column("exposed_ports", JSONB, nullable=True,
              comment="List of int ports to expose via sandbox tunnel "
                      "(e.g. [8443] for hosted-editor). Frozen per version."),
)
op.add_column(
    "environment_versions",
    sa.Column("persistent_volume", Boolean,
              nullable=False, server_default="false",
              comment="Whether this version wants a workspace-scoped "
                      "volume mounted at /workspace. The volume's name is "
                      "derived from workspace_id at spawn, not stored."),
)
```
`volume_name` is deliberately NOT a column — it's derived at spawn time
from `task.workspace_id` per spec §15 §4 #3.

**QA**: upgrade/downgrade cycle. Save `\d environment_versions` before/
after. Assert `credentials` and `egress` columns still present (no drift).
**Must not**: Don't add these to `environments`. Don't add `volume_name`.

#### Task 7 — Spawner wiring for tunnels + volume (NET-NEW integration)
**Files**: `backend/omoi_os/services/daytona_spawner.py`,
`backend/omoi_os/services/sandbox_provider.py` (protocol update)

**Important finding (verified by explore agent 2026-04-24):** the current
Daytona wrapper has **zero** tunnel, port-exposure, or volume primitives.
Grep for `tunnel`, `expose_port`, `volume`, `mount` in `daytona_spawner.py`
returns nothing. This task is therefore a new integration, not a narrow
wiring change — scope it accordingly.

**What**:
1. Extend the `SandboxProvider` protocol (see
   `backend/omoi_os/services/sandbox_provider.py`) with two optional
   methods: `expose_port(sandbox_id, port) -> str (url)` and
   `mount_volume(sandbox_id, name, path) -> None`. Optional because not
   every provider supports them (LocalDockerProvider may not); the spawner
   checks capability with `hasattr`.
2. Implement both in `DaytonaProvider` using Daytona's SDK
   (`sandbox.get_preview_link()` for tunnels, `sandbox.create` with
   `volumes=[{name, mountPath}]` for volumes — verify exact method names
   against the installed daytona SDK version before coding).
3. In `daytona_spawner.py` after sandbox creation: if resolved
   `env_version.exposed_ports` is non-empty AND provider supports tunnels,
   iterate, call `expose_port`, write `{port: url}` dict into
   `task.result['tunnel_urls']` (jsonb column already exists).
4. If `env_version.persistent_volume` is true AND provider supports
   volumes AND `task.workspace_id is not None`, synthesise
   `volume_name = f"ws-{task.workspace_id}"` and add it to the sandbox
   create call. Ticket-less sessions always have `workspace_id`; legacy
   ticket-driven sessions without a workspace silently skip the volume
   (backwards compatible).
5. Task 5's response synthesiser reads `task.result['tunnel_urls']` to
   populate `session.urls.editor` (first port by convention; a future plan
   can let the environment declare which port is the editor).

**QA**: Live spawn a ticket-less session whose pinned environment_version
has `exposed_ports=[8443]`; assert Daytona returned a tunnel URL and
`task.result['tunnel_urls']['8443']` contains `https://...`. Second spawn
against the same workspace with `persistent_volume=true` — write file in
sandbox A via ssh-exec, terminate A, spawn B in same workspace, assert
file present.
**Must not**: Don't read ports from the parent `environments` row — only
from the pinned `environment_versions`. Don't cache `volume_name` on the
task — derive at spawn. Don't make the new protocol methods mandatory —
optional via `hasattr`, so `LocalDockerProvider` doesn't need to implement
them on day one.

#### Task 8 — Egress conformance test
**Files**: `backend/tests/integration/test_egress_conformance.py` (new)
**What**:
- Spawn a Daytona sandbox with `FEATURE_EGRESS_PROXY_ENABLED=true` +
  environment-level `allowed_hosts=['api.anthropic.com']`
- Exec `curl -s -o /dev/null -w "%{http_code}" http://api.evil.com` → non-200
- Exec `curl -s -o /dev/null -w "%{http_code}" https://api.anthropic.com/v1/messages`
  → 401 (reached the API — anthropic rejects empty auth) = proof host was
  allowed
- Assertions: `evil.com` blocked, `anthropic.com` allowed
**QA**: Save both curl outputs. Gate on `DAYTONA_API_KEY` env var.

### Wave 4 — SDK polish

#### Task 9 — Telemetry callback
**Files**: `sdk/python/omoios/client.py`, `sdk/typescript/src/client.ts`
**What**: New optional kwarg `telemetry: Callable[[TelemetryEvent],
Awaitable[None] | None] = None`. Emit events:
- `{kind: "request", method, path, headers_sanitized, body_size}`
- `{kind: "response", method, path, status, duration_ms}`
- `{kind: "stream_open", path, duration_ms}`
- `{kind: "stream_close", path, frames_received, duration_ms}`
- `{kind: "error", method, path, exception_type, message}`
Emit around every `_request` call + `aconnect_sse`/`fetch` stream hooks.

**QA**: Unit test — mock callback captures events across a full create +
events + reply flow; assert all five event kinds seen.

#### Task 10 — AbortSignal / CancelScope propagation
**Files**: `sdk/typescript/src/resources/sessions.ts`,
`sdk/python/omoios/resources/sessions.py`
**What**: Add `signal?: AbortSignal` param to `create()`, `reply()`, `get()`,
`list()`, `fork()`, `share()`, `cancel()` (TS); add `cancel_scope: Optional
[anyio.CancelScope]` to the Python analogues. Propagate into the underlying
`fetch` / `httpx` call.

**QA**: TS — `AbortController` abort before create; assert `AbortError`.
Python — `asyncio.wait_for(create(...), timeout=0.01)` raises TimeoutError
AND no in-flight HTTP connection lingers.

#### Task 11 — Docs
**Files**: `docs/architecture/session-channel-scaling.md` (new);
`sdk/python/README.md`, `sdk/typescript/README.md` (update)
**What**: ASCII sequence diagram of multi-replica WS + Redis flow; one-
line examples for each of the four SDK primitive patterns (A/B/C/D) + the
new `telemetry` callback. Cross-link spec §07 and §18.

---

## Final Verification Wave

### F1 — Multi-replica multiplayer
Boot two uvicorn replicas on 18001/18002 via docker-compose; run
`pytest backend/tests/integration/test_session_channel_multi_replica.py`
(new); assert both pattern-D primitives (presence + cursor.moved) cross
the replica boundary. Save `.sisyphus/evidence/spec-18-alignment/f1-multi-
replica.json`.

### F2 — Full smoke
`uv run python scripts/smoke_agent_platform.py --only session_create,
session_create_ticketless,session_get,session_events,session_reply,
session_fork,session_share,session_channel_multi_replica,usage_current,
connections_list,urls_populated,egress_conformance
--report .sisyphus/evidence/spec-18-alignment/f2-smoke.json`.

### F3 — OpenAPI + SDK parity
- `curl :18000/openapi.json | jq '.paths | keys[]' > after.txt`
- Diff against a pre-plan snapshot; assert `/api/v1/connections/*`,
  `/api/v1/usage/*` present
- Diff `SessionResponse` schema; assert `urls` + `usage` objects present
- Count resources on each SDK client: Python has `AsyncOmoiOSClient.{sessions,
  environments, credentials, artifacts, webhooks, workspaces, connections,
  usage}` = 8; TS same. Spec §18 §2 canonical 7 + our workspaces = 8 ✓

---

## Commit Strategy

One commit per task. Wave-level PRs land atomically. Format:
```
feat(spec-18): <task summary>

- <change 1>
- <change 2>

QA: <evidence file path>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Wave 1 is shippable on its own — it's a hotfix for the live regressions.
Wave 2 fills the SDK surface. Wave 3 is additive (no runtime behavior
change unless tenant sets `exposed_ports`). Wave 4 is pure polish.

---

## Success Criteria

1. `GET /api/v1/sessions` returns ticket-less sessions for their creator
2. Multi-replica multiplayer integration test PASSes
3. `redis-cli PUBSUB CHANNELS 'events.*'` shows per-session channels, not
   a single firehose
4. SDK exposes 8 resources (7 from spec §18 + workspaces)
5. `telemetry` callback fires for every request + stream event
6. AbortSignal / CancelScope cancels in-flight HTTP on both SDKs
7. `Session.urls.{events_sse, websocket, editor}` populated on GET
8. `Session.usage.{compute_seconds, tokens_input, tokens_output}` populated
9. Egress conformance: `api.evil.com` blocked, `api.anthropic.com` allowed
10. `alembic upgrade head` + `alembic downgrade -1` clean for 072
11. `just test-all` green; `pnpm test` green; `uv run pytest sdk/python/tests/`
    green

---

## Out of Scope (Deferred)

- **Modal provider adapter** — spec §15 work, deferred to a later plan
  once we've run the Daytona path through the new columns for a quarter
- **OpenCode/OmO agent runtime** — spec §14, fully deferred; our runtime
  is Claude Agent SDK / OpenHands
- **Better Auth migration** — spec §17 §6 explicitly advises against;
  skipped
- **Warm-pool sandbox allocation** — spec §15 §8; revisit only when
  p95 session-start latency breaches product SLO
- **Chrome extension with ReactGrab (spec §18 §5)** — prototype-level, not
  platform work
- **`Environment.image.kind="registry"`** — Modal-specific, deferred with
  Modal adapter
- **Snapshot-restore fast-starts** — blocked on Modal TS SDK roadmap
- **Per-agent fallback chains** — spec §14 §4, OmO-specific
- **BYO-compute (tenant-owned Modal workspaces)** — spec §15 §3, Phase 7
- **Removing the legacy `events.{entity_id}` publish** — kept for one
  release window; drop in a follow-up plan
- **Dropping `tasks.ticket_id` column** — multi-quarter deprecation
