# Sisyphus plan · Postgres → Redis Outbox Forwarder

**Goal**: any writer (API, sandbox agent, taskiq worker, raw SQL) inserts a row
into `event_outbox` inside its transaction; a forwarder process drains the
table to Redis pub/sub, woken by `LISTEN/NOTIFY`. Adding a new event source
is one `INSERT INTO event_outbox` and one `SUBSCRIBE` — no per-table glue.

**Shape**: priors-first probes under `scripts/poof_outbox/`, per-step state
cached at `.sisyphus/outbox-state/<probe>.json`, evidence written to
`.sisyphus/evidence/outbox-<ts>.json`. Each step is independently re-runnable
via `--step N` and skips if its cache is valid.

---

## Done-ness signal

`just poof-outbox-run-fresh` (≤30s on warm system):

```
[step 0] preflight              PASS  (db reachable, redis reachable)
[step 1] schema migration       PASS  (event_outbox + trigger present)
[step 2] writer helper          PASS  (emit() inserts + commits cleanly)
[step 3] notify wakes forwarder PASS  (LISTEN receives within 100ms)
[step 4] forwarder drains       PASS  (10 events → 10 redis publishes)
[step 5] watermark persists     PASS  (restart resumes from last id)
[step 6] crash recovery         PASS  (kill -9 mid-batch → no loss/dup)
[step 7] burst throughput       PASS  (1000 events ≤ 2s, no errors)
[step 8] subscriber fanout      PASS  (2 SUBSCRIBE clients each get all)
[step 9] direct-write path      PASS  (sandbox-agent INSERT publishes)
```

Exit 0 = ship.

---

## Step 0 · Preflight

**Why**: nothing else works without DB + Redis; fail loud, fail first.

**Probe**: `scripts/poof_outbox/00_preflight.py`
- Connect to `DATABASE_URL`, run `SELECT 1`
- Connect to `REDIS_URL`, run `PING`
- Confirm `psycopg[binary,pool]>=3.2` is importable (need `conn.notifies()`)

**Cache**: `.sisyphus/outbox-state/00_preflight.json` with `{db_url, redis_url, psycopg_version, ts}`. Skips if same URLs and ≤24h old.

**Pass**: both reachable, psycopg async-NOTIFY API present.

---

## Step 1 · Schema migration

**Why**: outbox table + trigger is the only DDL we add. Must be reversible.

**Deliverables**:
- `backend/alembic/versions/<rev>_event_outbox.py`
  - `event_outbox(id BIGSERIAL PK, topic TEXT, op TEXT, row_id UUID, payload JSONB, created_at TIMESTAMPTZ)`
  - `idx_event_outbox_id` (already PK), `idx_event_outbox_created_at`
  - `forwarder_state(name TEXT PK, watermark BIGINT, updated_at TIMESTAMPTZ)`
  - `outbox_notify()` plpgsql function + `AFTER INSERT FOR EACH STATEMENT` trigger
- Downgrade path: drop trigger, drop function, drop tables.

**Probe**: `scripts/poof_outbox/01_schema.py`
- Run `alembic upgrade head` against test DB if step is dirty
- `SELECT to_regclass('event_outbox')` is not null
- `SELECT prosrc FROM pg_proc WHERE proname='outbox_notify'` contains `pg_notify`
- Trigger exists on `event_outbox` and is `STATEMENT` level (not `ROW`) — bulk-insert safety

**Cache**: hash of the migration file + alembic head; invalidates when either changes.

**Pass**: all four assertions green.

---

## Step 2 · Writer helper

**Why**: every writer in the codebase calls one function. No raw SQL scattered.

**Deliverables**:
- `backend/omoi_os/services/event_outbox.py` exporting:
  ```python
  async def emit(conn, *, topic: str, row_id: UUID,
                 payload: dict, op: str = "insert") -> None
  ```
- Sync variant `emit_sync(conn, ...)` for the sandbox agent (which uses
  blocking `psycopg.Connection`)
- Both reuse the caller's connection — never open a new one — so the INSERT
  lands inside the caller's transaction.

**Probe**: `scripts/poof_outbox/02_writer.py`
- Open one txn, `emit(conn, topic="probe", row_id=uuid4(), payload={"x":1})`
- COMMIT, then `SELECT * FROM event_outbox WHERE topic='probe'` → exactly 1 row
- Roll back another txn after `emit(...)` → no rows persisted (proves it's
  inside the caller's txn, not autocommit)

**Cache**: hash of `event_outbox.py`.

**Pass**: 1 row after commit, 0 rows after rollback.

---

## Step 3 · NOTIFY wakes the forwarder

**Why**: the wake signal is what makes this near-realtime instead of polling.

**Deliverables**:
- `backend/omoi_os/services/outbox_forwarder.py` with a `Forwarder` class:
  - One `psycopg.AsyncConnection(autocommit=True)` for `LISTEN outbox_ready`
  - One regular pool for `SELECT FROM event_outbox`
  - `async def run(self)`: wake on NOTIFY *or* 1s timeout, drain in batches
    of 1000, update watermark, loop

**Probe**: `scripts/poof_outbox/03_notify.py`
- Start `Forwarder` in a background task with a stub `redis.publish` recorder
- `emit(...)` one row in a separate connection
- Assert recorder sees the publish within **200ms** of commit

**Cache**: hash of forwarder file.

**Pass**: latency well under 200ms (typical 5–20ms).

---

## Step 4 · Forwarder drains in order

**Why**: ordering is the contract — consumers must see events in `id` order.

**Probe**: `scripts/poof_outbox/04_drain.py`
- `emit(...)` 10 rows with sequential payloads `{n:0..9}`
- Assert recorder gets exactly 10 publishes, in order, no gaps, no dupes
- Assert each publish payload includes `topic`, `id`, `op`, `payload`

**Pass**: 10 in, 10 out, ordered.

---

## Step 5 · Watermark persists across restart

**Why**: forwarder dying mid-stream must not replay-storm Redis.

**Probe**: `scripts/poof_outbox/05_watermark.py`
- Emit 5 rows, run forwarder until drained, stop it
- Inspect `forwarder_state.watermark` = last emitted id
- Emit 5 more rows
- Start a fresh forwarder instance — assert it publishes only the 5 new ones,
  not all 10

**Pass**: zero replays of pre-watermark events.

---

## Step 6 · Crash recovery

**Why**: SIGKILL mid-batch is the realistic failure mode.

**Probe**: `scripts/poof_outbox/06_crash.py`
- Emit 100 rows
- Start forwarder in subprocess with batch_size=10
- After it processes 25–50, send SIGKILL
- Inspect: how many rows did Redis recorder see? Watermark in DB?
- Restart forwarder
- Assert: total_published_after_recovery ∈ [100, 110] (at-most-once-batch
  duplication of the in-flight batch is acceptable; no loss)

**Pass**: no lost rows; ≤10-row duplication window.

---

## Step 7 · Burst throughput

**Why**: prove it isn't a toy. Sandbox agent will burst-write.

**Probe**: `scripts/poof_outbox/07_burst.py`
- One `emit_many` call inserts 1000 rows in one statement (tests the
  `FOR EACH STATEMENT` trigger — should fire ONE NOTIFY, not 1000)
- Time from commit to watermark = 1000
- Assert: ≤2s end-to-end, ≥500 events/sec sustained
- Assert: `pg_stat_activity` shows the LISTEN connection idle most of the
  time (not spinning)

**Pass**: 1000 events drained in <2s, no errors logged.

---

## Step 8 · Subscriber fanout

**Why**: this is what unlocks "add a table, just SUBSCRIBE."

**Probe**: `scripts/poof_outbox/08_fanout.py`
- Two Redis `SUBSCRIBE` clients on `changes:probe`
- Emit 20 rows
- Both clients receive all 20, identical order
- Add a third client subscribing to `changes:other` mid-flight — receives 0
  (proves topic isolation)

**Pass**: full fanout, no cross-topic bleed.

---

## Step 9 · Direct-write path (the real motivator)

**Why**: the sandbox agent writes to DB without going through the API.

**Probe**: `scripts/poof_outbox/09_direct_write.py`
- Open a *fresh* psycopg connection (simulating sandbox agent — no FastAPI
  dependency, no Redis client)
- In one transaction: `INSERT INTO session_events (...)` + `emit(...)`
  with `topic="session_events"`
- Assert: a `SUBSCRIBE changes:session_events` consumer gets the publish
- Assert: rolling back the txn → consumer gets nothing (atomicity proof)

**Pass**: direct-DB-write reaches Redis with no extra plumbing.

---

## Wiring after all probes pass

These are *follow-up commits*, gated on `just poof-outbox-run-fresh` green.

| Site | Change |
|---|---|
| `backend/omoi_os/api/routes/sessions.py` | Replace explicit `redis.publish(...)` calls in `SessionEventEnvelope.emit()` with `event_outbox.emit(conn, topic="session_events", ...)` |
| `backend/omoi_os/services/chat_responder.py` | Same swap on agent-message emit path |
| `backend/omoi_os/services/sandbox_provider*.py` | Sandbox writers (Modal/Daytona paths) call `event_outbox.emit_sync(conn, ...)` |
| `backend/omoi_os/main.py` (lifespan) | Start `Forwarder.run()` as a fire-and-forget task; one per replica is fine |
| `Justfile` | `poof-outbox-run`, `poof-outbox-run-fresh`, `poof-outbox-step <N>` recipes mirroring the poof pattern |
| `docs/cli/api-reference.md` | Note that `session.*` events flow via outbox now (no consumer-visible change) |

The SSE/WS paths **do not change**. They still `SUBSCRIBE changes:session_events`. The forwarder is a transparent shim.

---

## Operational guardrails (after ship)

- Cron `DELETE FROM event_outbox WHERE created_at < now() - interval '7 days'`
  every hour (or partition by day and drop partitions).
- Alert on `(SELECT max(id) FROM event_outbox) - watermark > 10000` —
  forwarder is falling behind.
- Alert on forwarder process exit (Railway/Modal restart policy).
- Optional: a `forwarder_metrics` table that the forwarder UPDATEs every N
  batches with rows/sec, lag, last_publish_ts. Cheap, surfaces in Grafana.

---

## What this plan deliberately does NOT include

- Schema-change capture for arbitrary tables (CDC). If you want updates to
  *existing* rows in unrelated tables to flow, add CDC later — not now.
- Dead-letter queue for poison messages. Add when we see one.
- Multi-region / cross-cluster fanout. NOTIFY is local to the primary.
- Forwarder horizontal scaling. One process handles >5k events/sec; revisit
  with sharded watermarks only if we exceed that.

---

## Why this is the Sisyphus shape

Each probe is small (≤80 LOC), has a binary pass/fail, caches its evidence,
and refuses to re-prove what's already green. Re-runs are cheap, debug loops
are surgical (`--step 6` to repro a crash without re-running 0–5), and the
final `run-fresh` is the integration acceptance. The forwarder ships when —
and only when — every probe is green on a clean cache.
