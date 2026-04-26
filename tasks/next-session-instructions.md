# Next Session — Run Order

**Single goal**: observe one session go pending → running → succeeded
with an agent making a real Fireworks Kimi LLM call.

If you finish this in <60 minutes you can move on to terminal-first
provider/onboarding CLIs. If it takes longer — you're hitting real
infra issues; document them and stop. Don't pile features on top of an
unverified loop.

## 0 · Read these first (5 min)

1. `MEMORY.md` (auto-loaded) — confirm `project_proof_of_life_setup`
   memory still reflects reality.
2. `tasks/agent-proof-of-life-plan.md` — full plan with rationale +
   risks. This file is the *runbook*; that one is the *spec*.
3. Skim `docs/agent-platform-analysis/client-pattern-experiments.md`
   "Gap-closure history" section to remember which phases are pinned.

## 1 · Pre-flight — verify nothing has rotted (3 min)

Run from repo root `/Users/kevinhill/Coding/Experiments/senior-sandbox/omoi_os`:

```bash
# (a) API healthy
curl -s -o /dev/null -w "status=%{http_code} time=%{time_total}\n" \
  --max-time 10 https://api.omoios.dev/health
# Expect: status=200 time=<2s

# (b) Orchestrator + sandbox provider + Fireworks key all set
railway variables | grep -E "MONITORING_ORCHESTRATOR_ENABLED|MONITORING_ENABLED|SANDBOX_PROVIDER|FIREWORKS_API_KEY"
# Expect:
#   MONITORING_ORCHESTRATOR_ENABLED=true
#   MONITORING_ENABLED=false  (KEEP IT OFF — flipping on overwhelmed the API last time)
#   SANDBOX_PROVIDER=modal
#   FIREWORKS_API_KEY=fw_… (lowercase fw_, NOT Fw_)

# (c) Orchestrator is actually claiming tasks
railway logs --deployment 2>&1 | grep "Assigned task to agent" | tail -3
# Expect: at least one assignment in last 24h. If empty, see Triage A.

# (d) Smoke account is fresh
ls -la backend/.env.smoke-test
# If older than 24h, run: uv run --with httpx --with psycopg --with passlib --with bcrypt python scripts/setup_prod_smoke_account.py
```

**Stop and triage if any of (a)-(d) fail.** Don't proceed to step 2.

## 2 · Patch the renderer to know about Fireworks (10 min)

File: `backend/omoi_os/services/opencode_config_renderer.py`.

Add to `_KNOWN_PROVIDERS`:

```python
"fireworks": {
    "npm": "@ai-sdk/openai-compatible",
    "name": "Fireworks AI",
    "options": {
        "baseURL": "https://api.fireworks.ai/inference/v1",
        "apiKey": "{env:FIREWORKS_API_KEY}",
    },
},
```

Add to `_DEFAULT_MODELS`:

```python
"fireworks": "fireworks/accounts/fireworks/routers/kimi-k2p5-turbo",
```

Add `"fireworks"` to `_PREFERENCE_ORDER` *as the FIRST entry* — when it's
present in an env_version, it should be the default.

Smoke-test the renderer locally:

```bash
uv run python -c "
from backend.omoi_os.services.opencode_config_renderer import render_opencode_config
print(render_opencode_config(['fireworks']))
"
```

Should print a JSON object with `provider.fireworks.options.baseURL` set
correctly. **Verify the `model` field renders as
`fireworks/accounts/fireworks/routers/kimi-k2p5-turbo`** — slashes and
all. If OpenCode rejects this format, see Triage B.

Commit + push. Wait ~90s for Railway redeploy.

## 3 · Run the proof-of-life script (15 min)

Save this as `scripts/agent_proof_of_life.py`:

```python
#!/usr/bin/env python3
"""Single-shot end-to-end agent run against Fireworks Kimi K2.5."""
import asyncio, os, sys, time, json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "sdk" / "python"))

from omoios import AsyncOmoiOSClient

async def main() -> int:
    api = os.environ["OMOIOS_API_BASE_URL"]
    key = os.environ["OMOIOS_PLATFORM_API_KEY"]
    ws  = os.environ["OMOIOS_TEST_WORKSPACE_A"]
    org = os.environ["OMOIOS_TEST_ORG_ID"]
    fw  = os.environ.get("FIREWORKS_API_KEY")
    if not fw:
        print("FIREWORKS_API_KEY not set in shell — source .env.smoke-test")
        return 1

    async with AsyncOmoiOSClient(base_url=api, api_key=key, timeout=60.0) as c:
        # 1. Bind Fireworks key as a workspace credential
        binding = await c.credentials.create(
            workspace_id=ws, kind="bearer_secret",
            name=f"fireworks-poc-{int(time.time())}", value=fw,
        )
        print(f"  ✔ binding {binding.id[:8]}…")

        # 2. Create env + bound version
        env = await c.environments.create(organization_id=org, name=f"kimi-poc-{int(time.time())}")
        ev_resp = await c._request(
            "POST", f"/api/v1/environments/{env.id}/versions",
            json={
                "image": "nikolaik/python-nodejs:python3.12-nodejs22",
                "credentials": {
                    "fireworks": {"kind": "bearer_secret", "binding_id": binding.id},
                },
            },
        )
        env_version = ev_resp.json()
        print(f"  ✔ env_version {env_version['id'][:8]}…")

        # 3. Spawn session
        session = await c.sessions.create(
            workspace_id=ws,
            environment_id=env.id,
            prompt="Explain in 3 bullets how OpenCode finds its provider keys.",
            metadata={"source": "proof-of-life", "ts": time.time()},
        )
        print(f"  ✔ session {session.id[:8]}…")

        # 4. Stream events until terminal
        deadline = time.time() + 300  # 5 min budget
        terminal = {"session.succeeded", "session.failed", "session.cancelled"}
        seen_types: list[str] = []
        async for evt in c.sessions.events(session.id):
            seen_types.append(evt.type)
            print(f"    seq={evt.seq:>3} {evt.type:<28} actor={evt.actor}")
            if evt.type in terminal:
                print(f"\nTERMINAL: {evt.type}")
                break
            if time.time() > deadline:
                print("\nTIMEOUT after 5min")
                break

        # 5. Final shape check
        final = await c.sessions.get(session.id)
        print(f"\nfinal_status={final.status}")
        artifacts = await c.sessions.artifacts(session.id)
        print(f"artifacts={len(artifacts)}")
        for a in artifacts[:3]:
            print(f"  • {a.name} ({a.size_bytes}B)")

        # Persist evidence
        evidence_path = REPO / ".sisyphus" / "evidence" / f"agent-proof-of-life-{int(time.time())}.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps({
            "session_id": session.id,
            "final_status": final.status,
            "event_types": seen_types,
            "artifact_count": len(artifacts),
        }, indent=2))
        print(f"\n  ✔ evidence: {evidence_path}")

        return 0 if final.status == "succeeded" else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

Run it:

```bash
set -a && source backend/.env.smoke-test && set +a
uv run python scripts/agent_proof_of_life.py
```

## 4 · Success criteria

- Final event ∈ `{session.succeeded, session.failed, session.cancelled}`
- `final.status == "succeeded"`
- Event stream contains at least one `session.message` with
  `actor=agent` (proves the LLM was actually called, not just a status
  flip)
- Total wall-clock < 5 min

If all four hit: **commit the script** so it becomes a permanent
runnable proof. Then move to next-up CLI work (provider mgmt + GitHub
device-code auth — see `tasks/agent-proof-of-life-plan.md` discipline
notes).

## 5 · Triage by failure shape

**Triage A — orchestrator not claiming tasks.** Check
`MONITORING_ORCHESTRATOR_ENABLED=true` (NOT plain `ORCHESTRATOR_ENABLED`,
which goes to a different settings class). Re-set if missing. If still
not claiming after a redeploy, grep Railway logs for `orchestrator_loop`
errors.

**Triage B — OpenCode rejects the slashed model id.** The Fireworks
model `accounts/fireworks/routers/kimi-k2p5-turbo` has 3 slashes;
OpenCode's `provider/model` parser may stop at the first one. Two
fallbacks:
1. Define an explicit `models` block in the provider entry so the model
   key is just `kimi`:
   ```python
   "models": {"kimi": {"name": "Kimi K2.5 Turbo"}}
   ```
   And set the model field to `fireworks/kimi`.
2. URL-encode the slashes — but that's brittle, prefer (1).

**Triage C — auth.json missing inside the sandbox.** The bootstrap.sh
fetches from broker, but Modal sandboxes start with `sleep infinity` so
bootstrap never runs. Mirror what we did for opencode.json — write
auth.json directly via `sandbox.filesystem.write_bytes` in
`modal_spawner.py`. Pattern: fetch broker creds in the spawner using
the session token + render the auth.json shape inline. ~50 LOC.

**Triage D — session stuck in pending.** Orchestrator IS picking up
tasks (verified at session end), but if your specific session never
gets claimed: check `task.status` in DB directly. The task queue uses
priority + dependencies; a fresh ticketless session at MEDIUM priority
should claim within 60s. If >5 min: the session_acl insert may be
deadlocking. Look at `services/task_queue.py:enqueue_task`.

**Triage E — `session.failed` with cryptic error.** Pull the last 20
events; the agent's stderr usually shows up as a `session.message`
event with `actor=agent` carrying the error text. If empty, exec into
the still-running Modal sandbox via `modal sandbox exec` (use the
sandbox_id from `task.sandbox_id`).

## 6 · Hand-off if you can't finish

If proof-of-life doesn't land in this session, the *minimum* useful
thing to leave for the next session:

1. The `scripts/agent_proof_of_life.py` script (committed even if it
   currently fails) — it's the harness; bugs are easier to triage than
   to recreate.
2. `.sisyphus/evidence/agent-proof-of-life-<ts>.json` with whatever
   event sequence you observed, even if incomplete.
3. A note at the top of this file ("Next Session — Run Order") under a
   new "## Last attempt" header documenting:
   - Which step failed
   - Which Triage path was tried
   - The current hypothesis
4. If you flipped any Railway env vars to debug, **revert them before
   ending**. Especially `MONITORING_ENABLED` — never leave that on.

## 7 · After it passes, the queue is

Per `feedback_terminal_first.md` + the plan's discipline notes:

1. Provider control CLI — `omoios providers add/remove/list`,
   `omoios providers fallback set <chain>`. Build on `credentials` +
   `environments` resources we already have.
2. GitHub OAuth via device-code flow — `omoios auth github` opens
   `github.com/login/device`, polls for the token, stores via broker.
3. Tenant onboarding CLI — `omoios signup --email …`, programmatic
   API-key issuance. Today's `setup_prod_smoke_account.py` is the
   prototype; productize it.

Don't start any of these until proof-of-life is green and committed.
