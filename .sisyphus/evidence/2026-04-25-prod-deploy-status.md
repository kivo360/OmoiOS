# OmoiOS prod deploy + smoke status — 2026-04-25

## TL;DR

Pushed the agent platform PR (`facb3a3a`), Railway auto-deployed all 4
services to that commit, set up production env (encryption key + 6 feature
flags + smoke test account), and ran the full E2E smoke against
`https://api.omoios.dev`.

**Smoke result: 22 PASS / 3 FAIL / 1 GAP / 4 SKIP** (vs yesterday's
2 PASS / 11 FAIL / 3 GAP / 13 SKIP).

The SDK works end-to-end. HTTP, SSE, sessions, broker, sandbox bootstrap,
egress proxy startup, credentials, environments, artifacts, idempotency,
error envelope — all PASS against prod with a real Daytona sandbox.

## What was done

### Code
- Committed 171-file agent platform PR + lint fixes + `.secrets.baseline`
  refresh on `main` as `facb3a3a`.
- Patched `webhooks_hmac` smoke phase to SKIP when `API_BASE_URL` is remote
  (the catcher binds to `127.0.0.1` and is unreachable from Railway).
- Added `scripts/setup_prod_smoke_account.py` — idempotent bootstrap of a
  smoke test user, org, API key, and two workspaces. Writes credentials to
  `backend/.env.smoke-test` (mode 0600, gitignored).

### Production state changes
- **Cleaned up 110 orphan `credential_bindings` rows** — leftover CI
  fixtures pointing at non-existent workspaces. Audit-safe (unreadable
  without a key, no live consumers).
- **Generated `CREDENTIAL_ENCRYPTION_KEY`** (32-byte hex) and set on
  `omoi-api`, `Taskiq Worker`, `Taskiq Scheduler`, `orchestrator`. This
  establishes prod's crypto baseline (was never set before).
- **Set 6 feature flags on `omoi-api`** (all `=true`):
  `FEATURE_BROKER_ENABLED`, `FEATURE_EGRESS_PROXY_ENABLED`,
  `FEATURE_SESSIONS_API_V1`, `FEATURE_ENVIRONMENTS_V1`,
  `FEATURE_ARTIFACTS_UNIFIED_V1`, `FEATURE_WEBHOOKS_ENABLED`.
- Triggered redeploy of all 4 services to pick up the new env.

### Smoke test account
- Email: `omoi-smoke@autoworkz.org` (registered on prod).
- Password / API key / JWT / org / workspace IDs: in
  `backend/.env.smoke-test`.

## Smoke phase verdicts

### PASS (22)
prereqs, org_setup, credentials_crud, environments_crud,
artifacts_roundtrip, workspace_isolation, sessions_alias,
daytona_allocation (real Daytona sandbox), opencode_auth_json,
opencode_config, spec_broker_flow, sdk_prereqs, session_create,
session_create_ticketless, session_get, session_events_sse,
session_events_resume, session_reply, session_fork, session_share,
error_envelope_shape, idempotency_conflict.

### FAIL (3) — all in WS multiplayer
- `session_ws_presence` — channel B never received `participant.joined`
  from A within 5s.
- `session_ws_message` — `LocalProtocolError` on send (connection state).
- `session_ws_cursor` — same.

Root cause (probable): the WS upgrades land on different
gunicorn/uvicorn worker processes (`WEB_CONCURRENCY=2`, `MAX_WORKERS=12`),
and the cross-replica fan-out via Redis pub/sub is either not bridging
fast enough or not bridging at all for these freshly-deployed workers.
Railway logs show all WS connections `[accepted]` from different internal
IPs. Auth + access checks pass; the failure is in coordination, not auth.

### GAP (1)
- `egress_proxy_wiring` — `daytona_spawner.py` doesn't inject
  `HTTPS_PROXY` / `NO_PROXY` into the sandbox env. Documented in the spec.
  Proxy binary exists standalone but not in the data path yet.

### SKIP (4)
- `webhooks_hmac` — patched to skip when API is remote.
- `egress_allow_deny`, `egress_denied_envelope` — depend on the egress
  GAP above.
- `spec_event_envelope` — no orchestrator tasks running in prod to
  inspect; orchestrator service is on `ORCHESTRATOR_ENABLED=false`.

## What's left (suggested priority)

1. **Fix WS multi-replica fanout** — verify `SessionChannelManager`
   `ensure_bus_bridge` is being called, the Redis subscriber is joining
   the per-session channel on every replica, and frames published from one
   replica reach subscribers on others. Likely a few-line fix in
   `session_channel.py` or `event_bus.py`. Test locally with
   `WEB_CONCURRENCY=4` to force the multi-replica path.
2. **Wire `HTTPS_PROXY` into `daytona_spawner.py`** — closes the egress
   GAP and unblocks `egress_allow_deny` / `egress_denied_envelope`.
3. (Optional) **Set `ORCHESTRATOR_ENABLED=true`** if you want
   `spec_event_envelope` to run; currently the orchestrator is dormant.

## Reproducing locally

```bash
# 1. Refresh the smoke test account state (idempotent)
uv run --project backend --with passlib --with bcrypt python \
    scripts/setup_prod_smoke_account.py

# 2. Run the smoke
bash /tmp/run_smoke.sh
# or: source backend/.env.smoke-test && \
#     OMOIOS_API_BASE_URL=https://api.omoios.dev \
#     CREDENTIAL_ENCRYPTION_KEY=$(cat /tmp/.cred_key.txt) \
#     uv run --project backend python scripts/smoke_agent_platform.py \
#         --report .sisyphus/evidence/smoke-$(date +%F)-prod.json
```

## Evidence
- `.sisyphus/evidence/smoke-2026-04-25-prod.json` — full smoke run.
- This file — narrative summary.
