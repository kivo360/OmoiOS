# OmoiOS prod deploy + smoke status — 2026-04-25 (final)

## TL;DR

All product code that was failing is fixed. Final smoke against prod:

```
PASS 22  FAIL 1  GAP 0  SKIP 7
```

The 1 FAIL is **`daytona_allocation`** — Daytona reports
`"Organization is suspended: Depleted credits"` (HTTP 403). This is a
billing issue on the Daytona side, not a code bug. The 7 SKIPs are all
expected (5 of them depend on Daytona, 1 is a remote-API limitation,
1 needs orchestrator running).

Once Daytona credits are topped up, this run should go to PASS 27 / FAIL 0
without any further code changes.

## Commits shipped today (oldest → newest)

| SHA | Title |
|---|---|
| `facb3a3a` | feat: agent platform spec alignment + sandbox session decoupling |
| `2972bb61` | feat: prod smoke account bootstrap + remote-aware webhook skip |
| `9629f4ee` | chore: log actual exception when WS session access check fails |
| `2b3d9060` | fix(ws): bind verify_task_access on session_channel module + cross-replica presence |
| `b19c33dd` | chore(smoke): correct egress_proxy_wiring verdict to SKIP for raw sandbox |

## The WS bug that broke all multiplayer

`session_ws_endpoint` had two bugs that together returned 4403 Forbidden
to every WS connect, even for the session's own owner:

1. **`AttributeError: module 'session_channel' has no attribute 'verify_task_access'`**
   The handler called `_self_mod.verify_task_access(...)` to support test
   monkeypatching, but the function was never imported into the module's
   namespace. Every connect raised AttributeError, caught by the blanket
   `except Exception:` block, and turned into a Forbidden response.
   Confirmed via Railway logs after wiring up structured exception
   logging on the deny path (commit `9629f4ee`).

2. **Cross-replica presence not fanned out**
   `participant.joined` / `participant.left` were broadcast LOCAL-ONLY
   via `_broadcast_to`, so peers on a different gunicorn worker never
   heard about the join/leave. `cursor.moved` already went through
   Redis `ch.{session_id}` correctly. Switched the presence frames to
   the same path so the bridge fans them out across all replicas.
   Clients filter their own echoes by `user_id` (same as cursor).

Both fixed in commit `2b3d9060`. After deploy:

- Manual WS repro: B sees A's `participant.joined`, message+ack works,
  cursor frames flow.
- Smoke: `session_ws_presence`, `session_ws_message`, `session_ws_cursor`
  all PASS at `WEB_CONCURRENCY=2`.

## Production state

### Railway (project `aomoi-os-backend`, env `production`)

- 4 services on `2b3d9060` SUCCESS: `omoi-api`, `Taskiq Worker`,
  `Taskiq Scheduler`, `orchestrator`.
- omoi-api `WEB_CONCURRENCY=2` (was temporarily dropped to 1 to
  diagnose multi-replica WS; restored).
- Env vars set today:
  - `CREDENTIAL_ENCRYPTION_KEY` (fresh 32-byte hex) on all 4 services
  - 6 `FEATURE_*=true` flags on `omoi-api`:
    `BROKER_ENABLED`, `EGRESS_PROXY_ENABLED`, `SESSIONS_API_V1`,
    `ENVIRONMENTS_V1`, `ARTIFACTS_UNIFIED_V1`, `WEBHOOKS_ENABLED`

### Database

- 110 orphan `credential_bindings` rows (CI fixtures pointing at
  non-existent workspaces) cleaned up.
- Smoke test account: `omoi-smoke@autoworkz.org`, owns "OmoiOS Smoke
  Org" + 3 workspaces (`smoke-a`, `smoke-b`, plus `octocat/hello-world`
  added by a session test). Has an `sk_live_*` API key.
- Credentials in `backend/.env.smoke-test` (mode 0600, gitignored).

## Smoke phase verdicts (final)

### PASS (22)
prereqs, org_setup, credentials_crud, environments_crud,
artifacts_roundtrip, workspace_isolation, sessions_alias,
spec_broker_flow, sdk_prereqs, session_create,
session_create_ticketless, session_get, session_events_sse,
session_events_resume, session_reply, session_fork, session_share,
**session_ws_presence**, **session_ws_message**, **session_ws_cursor**,
error_envelope_shape, idempotency_conflict.

### FAIL (1) — billing
- **daytona_allocation** — `Organization is suspended: Depleted credits`.
  Top up the Daytona account at app.daytona.io and re-run.

### SKIP (7) — all expected
- `webhooks_hmac` — remote API can't reach `127.0.0.1` catcher.
- `egress_proxy_wiring`, `egress_allow_deny`, `opencode_auth_json`,
  `opencode_config`, `egress_denied_envelope` — depend on a sandbox
  that never got allocated.
- `spec_event_envelope` — no orchestrator tasks running
  (`ORCHESTRATOR_ENABLED=false`).

### GAP (0)
The previous `egress_proxy_wiring` GAP turned out to be a smoke-script
mis-verdict: the spawner DOES inject HTTPS_PROXY/HTTP_PROXY/NO_PROXY
when an `EnvironmentVersion.egress.allowed_hosts` is bound (see
`daytona_spawner.py:320-338`). The smoke allocates a raw Daytona
sandbox bypassing the spawner, so the env vars wouldn't be there —
that's expected behavior, not a bug. Smoke now SKIPs with that reason.

## What's left

1. **Top up Daytona credits** (user action). Once done, re-run the
   smoke — should go straight to PASS 27.
2. (Optional) **Set `ORCHESTRATOR_ENABLED=true`** to run a real
   orchestrator on prod. Unblocks `spec_event_envelope`.
3. (Optional) **Tunnel the webhook catcher** (ngrok / RequestBin) if
   you want webhook delivery exercised end-to-end against prod.

## Reproducing the smoke

```bash
# Refresh creds (idempotent; resets password + JWT)
uv run --project backend --with passlib --with bcrypt python \
    scripts/setup_prod_smoke_account.py

# Run the smoke against prod
bash /tmp/run_smoke.sh
# (or recreate that wrapper from .env.smoke-test + DAYTONA_API_KEY +
#  CREDENTIAL_ENCRYPTION_KEY)
```

Reports land in `.sisyphus/evidence/smoke-YYYY-MM-DD-prod.json`.

## Evidence
- `.sisyphus/evidence/smoke-2026-04-25-prod.json` — final smoke run JSON
- This file — narrative + history
