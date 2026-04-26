# Client Pattern Experiments

> Validates the OmoiOS implementation against `agent-platform-spec/18-sdk-and-client-patterns.md`.
> 30 use cases reduce to 4 primitive patterns + 7 auth patterns. Test
> the primitives first; if those pass, the use cases are derivative.

Each experiment has: **what it proves**, **setup**, **assertions**, and the **spec
section** it maps to. Run them in order — earlier ones are prereqs for later.

Many of these can run against `https://api.omoios.dev` using the credentials
that `scripts/setup_prod_smoke_account.py` produces in `backend/.env.smoke-test`.

---

## TL;DR — the matrix

| # | Experiment | Pattern | Auth | Spec § |
|---|---|---|---|---|
| 1 | Fire-and-forget creation + later poll | A | API key | 18 §3.A |
| 2 | Sync-wait until terminal status | B | API key | 18 §3.B |
| 3 | Live SSE stream with replay | C | API key | 18 §3.C, 06 |
| 4 | Multiplayer WS: presence + message + cursor | D | User JWT | 18 §3.D, 07 |
| 5 | Idempotent retry of create | A | API key | 02, 08 |
| 6 | Cancellation propagates AbortSignal | B | API key | 18 §1.5 |
| 7 | Auto-pagination on list endpoints | — | API key | 18 §1.3 |
| 8 | Fork from sequence number | A | API key | 18 §2 |
| 9 | Reply mid-session changes the trajectory | C | API key | 18 §2 |
| 10 | Share session with another user (RBAC grant) | A→D | API key + JWT | 18 §2, 01 |
| 11 | Auth scope: API key vs JWT vs session token | — | all 3 | 18 §6 |
| 12 | Session token bounded to broker only | — | session token | 04, 18 §6 |
| 13 | Error envelope shape conformance | — | any | 08 |
| 14 | Webhook delivery + HMAC verification | A | API key | 06 |
| 15 | Artifact upload/download roundtrip | A | API key | 02, 18 §13 |
| 16 | Custom metadata is opaque to SDK | A | API key | 18 §5 |
| 17 | Workspace isolation enforcement | — | API key | 02 |
| 18 | SDK runtime portability — Edge `fetch` shim | A | API key | 18 §6 (#28, #29) |
| 19 | CLI ergonomics: stdin, AbortSignal | B/C | API key | 18 §3 (#23) |
| 20 | Quota enforcement + 429 backoff signal | A | API key | 08 |
| 21 | OpenAPI shape match: SDK ↔ server schema | — | — | 18 §1.4 |
| 22 | No-SDK-state regression: parallel sessions | A×N | API key | 18 §7 |
| 23 | Public-demo proxy: API key never leaks to client | C | API key (proxied) | 18 §6 (#29) |
| 24 | RN/Worker `fetch` injection | A | API key | 18 §2 |
| 25 | Telemetry callback fires on stream events | C | API key | 18 §2 |

(25 experiments → covers the four primitives + the auth matrix + every
non-goal the SDK is supposed to honor. The 30 use cases all reduce to
these.)

---

## Primitive A — Fire-and-forget

### Experiment 1 — Create + later poll

**What it proves**: `sessions.create()` returns immediately with a stable id;
`sessions.get(id)` later reflects terminal status. Validates the most basic
server-side pattern (Slack bot, GitHub Action webhook, Cron job).

**Spec**: §3.A, mapped to use cases 1–9.

**Setup**:
```python
from omoios import AsyncOmoiOSClient
async with AsyncOmoiOSClient(base_url=API, api_key=KEY) as c:
    s = await c.sessions.create(workspace_id=WS, prompt="say hi")
    sid = s.id  # save and close client
# ... time passes, different process ...
async with AsyncOmoiOSClient(base_url=API, api_key=KEY) as c:
    s2 = await c.sessions.get(sid)
    assert s2.id == sid
    assert s2.status in {"running", "completed", "failed", "cancelled"}
```

**Assertions**:
- `create` returns < 2s (does NOT block on agent execution)
- `get` 5s later shows progress (status != "pending")
- `get` 60s later shows terminal status
- No SSE / WebSocket needed for this pattern

**What breaks if this fails**: every webhook-driven use case (Linear, GitHub,
Stripe, email-to-agent).

---

### Experiment 5 — Idempotent retry of create

**What it proves**: an `idempotency_key` on `create` collapses retried
requests to the same session id. Critical for at-least-once delivery from
Slack/Stripe/etc.

**Spec**: §02 (Resources), §08 (errors).

**Setup**:
```python
key = "idem-" + uuid4().hex
s1 = await c.sessions.create(workspace_id=WS, prompt="...", idempotency_key=key)
s2 = await c.sessions.create(workspace_id=WS, prompt="...", idempotency_key=key)
s3 = await c.sessions.create(workspace_id=WS, prompt="DIFFERENT", idempotency_key=key)
```

**Assertions**:
- `s1.id == s2.id` (same body, same key → dedup)
- `s3` returns 409 / IdempotencyConflict (different body, same key → reject)
- The smoke's `idempotency_conflict` phase already covers this end-to-end.

**What breaks if this fails**: every webhook integration with retry logic
(Stripe redelivers in 5 minutes if your endpoint times out).

---

### Experiment 14 — Webhook delivery + HMAC

**What it proves**: when a session changes state, the registered webhook
URL receives a POST with HMAC-SHA256 signature. Tenant verifies signature
to trust the payload.

**Spec**: §06.

**Setup**: spin up a tunneled receiver (ngrok, requestbin) since prod
can't reach `127.0.0.1`. Register subscription → trigger a state change →
verify signature.

**Assertions**:
- POST arrives within 30s of state change
- `X-Webhook-Signature` header matches `hmac_sha256(secret, body_bytes)`
- Replay is suppressed (exactly-once-per-event semantics)

**What breaks if this fails**: use cases 4 (Linear), 6 (Stripe), 7 (email-in).

---

## Primitive B — Synchronous wait

### Experiment 2 — Sync-wait via SSE

**What it proves**: a script can block on session completion using the
event stream, capturing the final status. Used by GitHub Actions,
Raycast, git pre-push hooks, `make` targets.

**Spec**: §3.B, mapped to use cases 1, 3, 21, 25, 26.

**Setup**:
```python
s = await c.sessions.create(workspace_id=WS, prompt="...")
async for ev in c.sessions.events(s.id):
    if ev.type in ("session.succeeded", "session.failed", "session.cancelled"):
        print(f"terminal: {ev.type}")
        break
```

**Assertions**:
- Loop terminates within session timeout (~5 min default)
- Final event type ∈ terminal set
- Exit code from script can be derived: `0` if `succeeded`, `1` otherwise
- The smoke's `session_events_sse` + `session_reply` phases already cover this.

---

### Experiment 6 — Cancellation via AbortSignal

**What it proves**: a client that calls `client.sessions.cancel(id)` —
or aborts the underlying request — actually stops the agent and emits
`session.cancelled`. Critical for CLIs (Ctrl+C), VS Code (extension
deactivation), and Edge Functions (10s budget).

**Spec**: §1.5 (cancellation propagation).

**Setup**:
```python
s = await c.sessions.create(workspace_id=WS, prompt="long task")
await asyncio.sleep(2)
await c.sessions.cancel(s.id)
async for ev in c.sessions.events(s.id):
    if ev.type == "session.cancelled":
        print("cancelled in", ev.timestamp); break
```

**Assertions**:
- `session.cancelled` appears in event stream within 5s
- Sandbox is terminated (check Modal/Daytona registry: no live sandbox for the task)
- Subsequent `get(id)` shows `status="cancelled"`, not "running"

**What breaks if this fails**: every CLI-based use case, every UI with a
"stop" button, every Edge runtime.

---

## Primitive C — Live stream

### Experiment 3 — SSE stream with `Last-Event-ID` resume

**What it proves**: the event stream is resumable by sequence number.
A client that reconnects after a brief disconnect doesn't lose events.

**Spec**: §3.C, §06.

**Setup**:
```python
events = []
async for ev in c.sessions.events(s.id):
    events.append(ev)
    if len(events) == 5: break

# reconnect, ask to resume after seq=3
async for ev in c.sessions.events(s.id, last_event_id=str(events[2].seq)):
    # should NOT include seq 1-3, but should include 4 and onwards
    assert ev.seq > 3
    if ev.seq >= events[-1].seq: break
```

**Assertions**:
- Resume returns events strictly after the given seq
- No event is duplicated across reconnects
- Closing and reopening doesn't reset the cursor server-side
- Already covered by smoke's `session_events_resume`.

**What breaks if this fails**: every dashboard/UI that needs to survive
network blips. Mobile apps especially.

---

### Experiment 9 — Mid-session reply changes trajectory

**What it proves**: an in-flight session accepts new user input and
incorporates it. Validates the "follow-up message" UX.

**Spec**: §2 — `sessions.reply(id, text)`.

**Setup**:
```python
s = await c.sessions.create(workspace_id=WS, prompt="research X")
# observe first agent response
await asyncio.sleep(5)
await c.sessions.reply(s.id, "actually focus on subtopic Y")
# Subsequent agent events should mention Y, not just X
```

**Assertions**:
- `reply` succeeds (200) on a running session
- Subsequent `session.message` events from `actor=agent` reference the new
  prompt content
- Already covered by smoke's `session_reply`.

---

### Experiment 25 — Telemetry callback observability

**What it proves**: the `telemetry` constructor option fires on stream
open/close, frame received, request issued — so SREs can wire to
DataDog/OpenTelemetry from outside the SDK.

**Spec**: §2.

**Setup**:
```python
events = []
client = AsyncOmoiOSClient(base_url=API, api_key=KEY,
                          telemetry=lambda e: events.append(e))
async with client as c:
    s = await c.sessions.create(workspace_id=WS, prompt="...")
    async for ev in c.sessions.events(s.id):
        if ev.type == "session.message": break
```

**Assertions**:
- `events` includes at least: `request`, `stream_open`, `frame`, `stream_close`
- Each has `path`, `duration_ms`, and `frames_received` (for streams)
- Already partially covered by `sdk/python/tests/test_telemetry.py`.

---

## Primitive D — Interactive multiplayer (WebSocket)

### Experiment 4 — Presence + message + cursor

**What it proves**: two channels on the same session see each other's
join/leave, exchange messages with delivery acks, and broadcast cursor
positions without persisting them.

**Spec**: §3.D, §07.

**Setup**: open `ch_a` and `ch_b` with the same user JWT (or two JWTs);
B subscribes to `participant.joined` and `session.message`.

**Assertions**:
- B receives `participant.joined` for A within 5s of A connecting
- A.send `message.send` → B receives `session.message`; A receives
  `message.ack` with the persisted seq
- A.send `cursor.moved` → B receives it; the events table has NO
  `cursor.moved` row (broadcast-only, ephemeral)
- All three smoke phases pass: `session_ws_presence`, `session_ws_message`,
  `session_ws_cursor` (already green at PASS 24 / FAIL 0).

**What breaks if this fails**: hosted-editor iframe (#11), multi-cursor
review (#14), VS Code sidebar (#20).

---

### Experiment 10 — Share session with another user

**What it proves**: `sessions.share(id, [{user_id, role: 'editor'}])`
grants a second user access to the WS channel; their actions appear with
their own `actor=user:<id>` actor.

**Spec**: §2, §01 (RBAC).

**Setup**:
1. Mint a second user account (different email)
2. Original owner: `share(s.id, [{user_id: u2.id, role: 'editor'}])`
3. u2 connects with their own JWT
4. u2 sends `message.send`

**Assertions**:
- u2's WS handshake succeeds (no 4403)
- `session.message` from u2 carries `actor=user:<u2.id>`
- A non-shared user gets 4403 — already verified by `workspace_isolation`
- Revoke (`share` with empty grants or `role: 'none'`) closes u2's WS

---

## Auth-pattern matrix

### Experiment 11 — All three token types route correctly

**What it proves**: the `Authorization: Bearer <token>` header is
classified by prefix and dispatched to the right verifier. No token
type is silently coerced to another.

**Spec**: §06 (auth patterns table).

**Setup**: probe `/api/v1/sessions` with each:
- `sk_live_…` (platform key) → 200, scope = whole org
- `eyJ…` (user JWT) → 200, scope = user's RBAC subset
- `sess_tok_…` (sandbox session token) → 401 (this endpoint isn't broker)
- random string → 401 with `error.code = "invalid_token"`

**Assertions**:
- Status codes match the table above
- Error envelope on rejection follows §08 shape
- Already validated indirectly by `prereqs` + `org_setup` + the WS auth path.

---

### Experiment 12 — Session token can ONLY hit the broker

**What it proves**: a `sess_tok_…` is bounded — it cannot list sessions,
read other workspaces' resources, or call any non-broker endpoint.

**Spec**: §04, §06 (last row of the table).

**Setup**: mint a session via `sessions.create`; capture the issued
`SESSION_TOKEN`. Probe each endpoint:

| Endpoint | Expected |
|---|---|
| `GET /broker/creds/<alias>` | 200 (with valid alias) |
| `GET /api/v1/sessions` | 401 |
| `GET /api/v1/credentials` | 401 |
| `GET /api/v1/workspaces` | 401 |

**Assertions**: only `/broker/*` returns 2xx; everything else 401.

**What breaks if this fails**: the entire credential broker security
model. Currently smoke's `spec_broker_flow` proves the route exists and
auth-rejects fake tokens; this is the orthogonal axis (real token →
bounded scope).

---

## Cross-cutting (SDK design discipline)

### Experiment 7 — Auto-pagination

**What it proves**: `sessions.list()` returns an async iterable that
walks pages transparently. Calling `len()`-equivalent semantics work.

**Spec**: §1.3.

**Setup**: create 25 sessions, then iterate `list()` with default page
size of 20.

**Assertions**:
- Total items yielded == 25
- The iteration spans ≥ 2 pages (server actually paginated)
- The SDK does NOT load all pages eagerly into memory (test with a
  generator that breaks after 5)

---

### Experiment 13 — Error envelope conformance

**What it proves**: every 4xx/5xx response from the API has the spec §08
envelope shape: `{error: {code, type, message, request_id}, detail?}`.

**Spec**: §08.

**Setup**: trigger 6 distinct error classes:
| Trigger | Status | Expected `error.code` |
|---|---|---|
| Missing auth | 401 | `unauthenticated` |
| Wrong workspace | 403 | `forbidden` |
| Unknown session id | 404 | `not_found` |
| Bad JSON body | 400 | `bad_request` |
| Validation failure | 422 | `validation_error` |
| Idempotency conflict | 409 | `idempotency_conflict` |

**Assertions**: every response has the same key set; no naked strings,
no inconsistent shapes. Smoke's `error_envelope_shape` is the prototype.

---

### Experiment 16 — Metadata is opaque

**What it proves**: arbitrary keys under `metadata` survive the
roundtrip and are visible to the agent runtime, but the SDK has no
schema for them. Validates the "ReactGrab pattern" in §5.

**Spec**: §18 §5.

**Setup**:
```python
meta = {
    "origin": "test-extension",
    "reactgrab": {"component": "Button", "filePath": "src/Button.tsx:42"},
    "your_custom_key": {"a": [1, 2], "b": True},
}
s = await c.sessions.create(workspace_id=WS, prompt="...", metadata=meta)
s2 = await c.sessions.get(s.id)
assert s2.metadata == meta  # exact equality
```

**Assertions**: arbitrary nested JSON survives. No keys silently
dropped, transformed, or rejected.

---

### Experiment 17 — Workspace isolation

**What it proves**: a credential / artifact / environment created in
workspace A is invisible from a request scoped to workspace B (even
with the same platform key).

**Spec**: §02.

**Setup**: covered by smoke's `workspace_isolation` phase. Manual repro:
```python
cred_a = await c.credentials.create(workspace_id=WS_A, ...)
items_b = [x async for x in c.credentials.list(workspace_id=WS_B)]
assert cred_a.id not in {i.id for i in items_b}
# direct GET should also 404/403
```

---

### Experiment 21 — OpenAPI shape match

**What it proves**: the SDK's generated types (Pydantic models /
TypeScript interfaces) match the live OpenAPI document exactly. No
silent drift.

**Spec**: §1.4.

**Setup**:
```bash
curl https://api.omoios.dev/openapi.json > /tmp/live-openapi.json
# compare against the SDK's frozen schema
diff <(jq -S . /tmp/live-openapi.json) \
     <(jq -S . sdk/python/openapi.fixture.json)
```

**Assertions**: clean diff (or only additions, never breaking changes).
This is the most likely place for "agent works in dev, not in prod"
type bugs.

---

### Experiment 22 — Stateless SDK under parallel sessions

**What it proves**: the SDK has no internal state shared across
sessions. Two `sessions.events()` iterators on different ids do NOT
interfere; closing one doesn't close the other.

**Spec**: §7 (no caching, no local state sync).

**Setup**:
```python
s1, s2 = await asyncio.gather(c.sessions.create(...), c.sessions.create(...))
async with asyncio.TaskGroup() as tg:
    tg.create_task(consume(c.sessions.events(s1.id)))
    tg.create_task(consume(c.sessions.events(s2.id)))
```

**Assertions**: both streams complete, neither cross-contaminates the
other's events, neither leaks a connection on early break.

---

## Runtime portability

### Experiment 18 — Cloudflare Worker `fetch` shim

**What it proves**: passing a custom `fetch` to the SDK constructor
makes it run in environments where the native `fetch` is non-standard
(Workers omit some headers; React Native's `fetch` lacks streaming
in some versions).

**Spec**: §6 (#28 Cloudflare Worker, #29 Vercel Edge).

**Setup**: write a tiny test that passes `node-fetch` (or a stub
recording calls) instead of the global. Run a `create` + `events`.

**Assertions**:
- All HTTP requests go through the injected fetch
- Headers include `Authorization`, `Idempotency-Key`, `User-Agent` per
  the spec
- SSE stream still parses (custom fetch must support `ReadableStream`)

---

### Experiment 19 — CLI ergonomics

**What it proves**: the SDK works in `ink`/`rich`-style CLIs:
- TTY detection
- Ctrl+C cancellation via signal → AbortSignal
- Stdin input → `reply()` mid-session
- Exit code from terminal status

**Spec**: §6 (#23–#27).

**Setup**: a one-file script `agent_do.py "..."` that:
1. creates a session
2. renders events with `rich.live.Live`
3. accepts stdin lines as follow-ups
4. exits with 0 on `succeeded`, 1 on `failed`, 130 on Ctrl+C

**Assertions**:
- Run in a TTY: spinner + live updates
- Run with `agent_do.py "..." | cat`: piped, no ANSI codes
- Send SIGINT mid-run: exits 130, session cancelled server-side

---

### Experiment 23 — Public-demo proxy

**What it proves**: a Vercel Edge Function holds the platform API key
server-side and proxies SSE to anonymous browser clients without
exposing the key. Cookie/IP-based quota enforced by Edge.

**Spec**: §6 (#29).

**Setup**: deploy a 30-line edge function:
- read `prompt` from request
- mint a session via SDK with the env-var key
- pipe `client.sessions.events(s.id)` back as `text/event-stream`

**Assertions**:
- Browser's network tab shows ONLY the edge URL — no `api.omoios.dev`
- Direct call to edge with a forged platform-key header is ignored
- Quota: 4th call from same IP returns 429 with `error.code = "quota_exceeded"`

---

## Anti-pattern checks (the SDK should NOT do these)

### Experiment 7b — No retries baked in

**What it proves**: when the SDK gets a 503, it returns the error
immediately. The CLIENT decides whether to retry, not the SDK.

**Spec**: §7 (non-goals).

**Setup**: point the SDK at a stub that returns 503 once, then 200.
Without your own retry, the call should fail. With your own retry
loop, it succeeds.

**Assertions**: the SDK does not transparently retry. The first call
raises; you must wrap it yourself.

---

### Experiment 7c — No client-side cache

**What it proves**: two calls to `sessions.get(id)` 1ms apart hit the
server twice. The SDK isn't memoizing.

**Spec**: §7.

**Setup**: instrument the injected `fetch` with a counter. Call
`get(id)` twice in a row.

**Assertions**: counter increments by exactly 2.

---

## Running the experiments

Most can be added as new phases in `scripts/smoke_agent_platform.py`.
The smoke already covers experiments 2, 3, 4, 5, 9, 11 (partially), 13,
17, 22 (implicitly).

**Gaps to close in the smoke** (in priority order):
1. Experiment 6 — cancellation + sandbox cleanup verification
2. Experiment 8 — fork from arbitrary seq
3. Experiment 10 — share + multi-user WS
4. Experiment 12 — session token bounded scope (security-critical)
5. Experiment 16 — metadata opacity (the ReactGrab claim)
6. Experiment 21 — OpenAPI drift detection (CI gate)

**Standalone** (don't fit in the smoke harness):
- Experiment 14 — needs a tunneled webhook receiver
- Experiment 18 — Cloudflare Worker harness
- Experiment 19 — interactive CLI in a TTY
- Experiment 23 — Edge Function deploy

---

## Per-use-case mapping

For confidence that each of the 30 use cases works, you only need to
verify the underlying primitives. This table is the cheat-sheet.

| Use case | Primitive(s) needed | Experiments that cover it |
|---|---|---|
| 1. Slack slash command | B + 14 webhook | 2, 5, 14 |
| 2. Discord bot with presence | D | 4, 10 |
| 3. GitHub Action | B | 2, 6, 19 (exit code) |
| 4. Linear webhook | A + 14 | 1, 5, 14 |
| 5. Cron health check | B + 14 | 2, 14 |
| 6. Stripe webhook → billing | A (consume) | 14 |
| 7. Email-to-agent | A + 14 | 1, 14, 16 (metadata) |
| 8. Postgres trigger | A | 1, 16 |
| 9. Token-exchange backend | A + JWT | 1, 11 |
| 10. Custom dashboard | C × N | 3, 22 |
| 11. Hosted-editor iframe | D | 4 |
| 12. Public demo | C, proxied | 3, 20, 23 |
| 13. Shareable replay | A + artifact | 1, 15 |
| 14. Multi-cursor review | D | 4 |
| 15. Mobile app | C | 3, 18 (RN fetch) |
| 16. Plasmo extension | A | 1, 16 |
| 17. ReactGrab picker | A + metadata | 1, 16 |
| 18. Firefox extension | A | 1, 16 |
| 19. Safari extension | A | 1, 16 |
| 20. VS Code sidebar | C | 3, 6 |
| 21. Raycast | B | 2, 19 |
| 22. JetBrains plugin | C | 3 |
| 23. Local CLI | C/B | 3, 19 |
| 24. tmux per-tab | C × N | 3, 22 |
| 25. Git pre-push | B | 2, 19 |
| 26. Make target | B | 2, 19 |
| 27. Shell hook | A | 1 |
| 28. Cloudflare Worker | A, custom fetch | 1, 18 |
| 29. Vercel Edge demo | C, proxied | 3, 23 |
| 30. Zapier/n8n | A | 1, 14 |

If experiments 1–4 + 14 + 18 + 23 pass, all 30 use cases can be built.

---

## Reflective question

> "When you imagine yourself using the SDK six months from now, on a
> use case you haven't thought of yet — what's the shape of the method
> call you wish was there?"
>
> — spec §9

After running the experiments, write down the use case you tried that
required hacking around the SDK. If it was the same hack twice, that's
when the SDK gets a new method. Until then, the discipline is using
metadata + the four primitives.
