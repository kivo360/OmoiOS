# F2 — Regression Sweep

## SDK test suites (authoritative for SDK changes)

### Python SDK (`sdk/python`)
```
uv run pytest -q
70 passed, 23 skipped in 0.55s
```

Includes:
- `test_cancel_scope.py` — 2/2
- `test_telemetry.py` — 5/5
- `test_connections_usage.py` — 6/6
- Existing suites unchanged (mock client, resources, types)

### TypeScript SDK (`sdk/typescript`)
```
pnpm -s test
Test Files  3 passed | 1 skipped (4)
Tests       68 passed | 7 skipped (75)
```

Includes:
- `tests/telemetry.test.ts` — 5/5
- `tests/integration.test.ts` — 37/37
- `tests/mockClient.test.ts` — 26/26

## Backend touched-module sweep

```
cd backend
uv run pytest \
  tests/unit/services/test_event_bus_per_session.py \
  tests/unit/test_session_urls_usage.py \
  tests/integration/test_session_channel_multi_replica.py \
  -q
```

Passed:
- `test_event_bus_per_session.py` — 5/5 (publish_to_session shape, Redis-down no-op, subscribe/unsubscribe refcount)
- `test_session_urls_usage.py` — 5/5 (URL builder scheme mapping, usage aggregation)
- `test_session_channel_multi_replica.py` — 2/2 (cursor crosses replica boundary, no cross-session leakage — against live Redis)

## Known pre-existing gap (NOT a regression from this work)

Many backend integration/unit tests fail at setup with
```
psycopg.OperationalError: port 15432 failed: Connection refused
```

Root cause: `tests/conftest.py:254` falls back to
`postgresql+psycopg://postgres:postgres@localhost:15432/app_db` when
`DATABASE_URL_TEST` is unset. My local dev Postgres runs on the
unprefixed port 5432 (the project convention elsewhere uses 15432 for
containerized dev). Supplying `DATABASE_URL_TEST` with my local DB URL
hits a separate async-session fixture deadlock unrelated to this work.

Tests that **did** run against the live environment (SDK suites + the
three backend suites above) all passed.

## Live endpoint probes — F3

- `GET /api/v1/connections` → 200 `[]`
- `GET /api/v1/usage` → 404 "no org membership" (semantic, not 404-not-found)
- `GET /api/v1/usage/sessions/{id}` → 200 (after fixing `verify_task_access`
  param binding — see below)
- `GET /api/v1/sessions/{id}` → 200 with `urls` + `usage` populated
  (see `f3-session-enriched.json`)

## Bug found + fixed during probing

`/api/v1/usage/sessions/{session_id}` used `Depends(verify_task_access)`
which reads `task_id` from the request params. Because the path variable
is `session_id` (not `task_id`), FastAPI couldn't auto-bind and returned
422 "Field required". Fixed by calling `verify_task_access` inline inside
the route body, passing `task_id=session_id`. No change in the ACL chain
logic.
