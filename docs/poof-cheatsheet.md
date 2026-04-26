# Poof Cheatsheet

Quick reference for the proof-of-life harness + tmux session.
**Lane is Fireworks-only:** `fw_WZk1n8qVwHxTeNPK8JWZ6Y` →
`https://api.fireworks.ai/inference/v1` → `accounts/fireworks/routers/kimi-k2p5-turbo`.

---

## tmux survival kit (the 3 keys you need)

| Want | Keys |
|---|---|
| **List windows** (see what's running) | `Ctrl-B` then `w` |
| **Scroll up to read history** | `Ctrl-B` then `[`  · arrows / PgUp · `q` to exit |
| **Detach (leave running)** | `Ctrl-B` then `d` |

Switch windows: `Ctrl-B` then `0` / `1` / `2` / `3`.
Help: `Ctrl-B` then `?` (q to exit).
**Stuck? Just close the Terminal window (Cmd-W). The session keeps running.**

Common gotcha: hold Ctrl, **tap** B, **release Ctrl**, then tap the next key.

---

## Session layout

| Window | Name | What's there |
|---|---|---|
| 0 | api | uvicorn server (FastAPI on `:18000`) |
| 1 | poof | shell — run `agent_proof_of_life.py` here |
| 2 | logs | `tail -F /tmp/uvicorn-prod.log` |
| 3 | probes | shell — `psql` + `poof_probes.sh` |

---

## Lifecycle

```bash
# Open a NEW Terminal window with banner + safe attach
./scripts/poof_watch.sh

# Or attach in the current terminal
./scripts/poof_watch.sh --inline

# Status (without attaching)
./scripts/poof_tmux.sh status

# Start (idempotent — safe to call repeatedly)
./scripts/poof_tmux.sh start

# Tear down everything (uvicorn + session)
./scripts/poof_tmux.sh kill
# or:
./scripts/poof_watch.sh --kill
```

---

## Run the proof-of-life

Inside `poof:1` (the poof window):

```bash
# Full run, reusing cached resources
.venv/bin/python scripts/agent_proof_of_life.py

# Fresh run (clear cache → new session id)
rm -f .sisyphus/poof.state.json && .venv/bin/python scripts/agent_proof_of_life.py

# Just one step
.venv/bin/python scripts/agent_proof_of_life.py --step 7
```

From the **outside** (any other terminal — drives the session without attaching):

```bash
tmux send-keys -t poof:1 '.venv/bin/python scripts/agent_proof_of_life.py' Enter
```

---

## Inspect without attaching

```bash
# Snapshot any window's last 200 lines
tmux capture-pane -p -t poof:0 -S -200    # api (uvicorn)
tmux capture-pane -p -t poof:2 -S -200    # logs
tmux capture-pane -p -t poof:1 -S -200    # poof script output

# Health
curl -s http://localhost:18000/health

# Cached resource ids
cat .sisyphus/poof.state.json
```

---

## Debug a stuck session (layered probes)

```bash
SID=$(jq -r .session_id .sisyphus/poof.state.json)
SESSION_ID=$SID ./scripts/poof_probes.sh
```

Probes run in order; **first FAIL pinpoints the broken layer**:

1. session row in DB
2. `session.created` event present
3. **chat_responder fired** (agent message exists)
4. uvicorn log lines (best-effort)
5. **task.status transitioned** to `completed`
6. `session.succeeded` envelope written
7. SSE stream actually delivers terminal

Direct DB queries:

```bash
psql "$DATABASE_URL" -c "SELECT seq, event_type, actor, LEFT(payload::text,80) FROM events WHERE entity_id = '$SID' ORDER BY seq;"
psql "$DATABASE_URL" -c "SELECT id, status FROM tasks WHERE id = '$SID';"
```

---

## Files & locations

| Path | Purpose |
|---|---|
| `scripts/agent_proof_of_life.py` | Step-by-step proof-of-life orchestrator |
| `scripts/poof_probes.sh` | Layered DB/API probes for a session id |
| `scripts/poof_tmux.sh` | tmux session lifecycle (start/status/kill) |
| `scripts/poof_watch.sh` | Open the session in a new Terminal with banner |
| `scripts/modal_sandbox_smoke.py` | Bare Modal sandbox + opencode smoke (no API/DB) |
| `scripts/local_opencode_llm_smoke.sh` | Host-side opencode + Kimi smoke (isolated XDG) |
| `scripts/setup_local_smoke_account.py` | Idempotent local-smoke account bootstrap |
| `/tmp/uvicorn-prod.log` | Full uvicorn stderr (chat_responder traces) |
| `/tmp/poof-tmux.env` | Env file every window sources |
| `.sisyphus/poof.state.json` | Cached session/workspace/binding ids |

---

## Common error patterns

| Symptom | Likely cause | Fix |
|---|---|---|
| Step 7 hangs, no agent message | asyncio task GC or LLM call failed | grep `/tmp/uvicorn-prod.log` for `chat responder` — should be using `fire_and_forget` |
| `httpx.ReadTimeout` in chat_responder | LLM endpoint slow (Z.AI's GLM-4.7 reasons) | Lane should be Fireworks (`accounts/fireworks/routers/kimi-k2p5-turbo`); 120s timeout is the default |
| `module 'sentry_sdk.metrics' has no attribute 'incr'` | Sentry SDK v2 dropped metrics API | already patched — `sentry.py` uses `getattr(...)` |
| `ProviderModelNotFoundError` (OpenCode) | npm-loaded provider needs explicit `models` block | Use built-in `fireworks-ai` provider id in opencode.json — no override needed |
| Step 7 has agent message but `final.status != "succeeded"` | task didn't transition | `chat_responder` calls `update_task_status("completed")` after emit |

---

## Don'ts

- Don't `tmux attach` from an automated agent — use `capture-pane` / `send-keys`.
- Don't restart uvicorn unless code changed (cold start ~10s).
- Don't substitute the LLM provider — Fireworks Kimi K2.5 Turbo only.
- Don't commit `.sisyphus/poof.state.json` or evidence (already gitignored).
