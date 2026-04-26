# Agent End-to-End Proof of Life — Implementation Plan

**Created**: 2026-04-26
**Status**: Plan
**Goal**: Watch a real session go pending → running → succeeded with an
agent making a real LLM call and producing observable output.
**LLM**: Kimi K2.5 Turbo via Fireworks (OpenAI-compatible endpoint).

## Why this is the right next step

Bare-minimum platform shipped today (PASS 29 / FAIL 1 / GAP 0 / SKIP 5).
Every primitive contract is wired. What we have NOT yet observed end-to-end
is the closing-the-loop step: orchestrator picks pending → spawns sandbox →
agent makes a real LLM call → emits events → finishes. Once that lands
once on prod, every Ramp-style use case stops being theoretical.

## Non-goals for this run

- No GitHub integration yet (no PR creation, no clone). Just an LLM call
  that produces text output captured as an artifact or session message.
- No multi-tenant tests — single smoke account, single workspace.
- No frontend involvement — entirely terminal-driven, per the
  terminal-first principle.
- No Daytona — Modal only (free credits, already wired).

## Pre-flight checks (run first)

```bash
# 1. Orchestrator is on
railway variables | grep -E "MONITORING_ORCHESTRATOR_ENABLED|SANDBOX_PROVIDER"
# Expect: MONITORING_ORCHESTRATOR_ENABLED=true, SANDBOX_PROVIDER=modal

# 2. Smoke account credentials are fresh
ls -la backend/.env.smoke-test
# If older than ~1 hour: re-run setup_prod_smoke_account.py to refresh JWT

# 3. Fireworks key exists in Railway (set in this session, see step 1)
railway variables | grep FIREWORKS_API_KEY
```

## Step 1 — Stash the Fireworks key on Railway

The key the user provided lives in Railway, not in the repo. Set once:

```bash
railway variables --set "FIREWORKS_API_KEY=<the key>"
```

This is the env-var fallback for the bootstrap path. The PRIMARY credential
delivery is via the broker — see step 3.

## Step 2 — Teach the renderer about Fireworks

`backend/omoi_os/services/opencode_config_renderer.py` knows about
anthropic / openai / openrouter / google / groq / xai today. Add a
`fireworks` entry:

```python
"fireworks": {
    "npm": "@ai-sdk/openai-compatible",  # OpenAI-compatible adapter
    "name": "Fireworks AI",
    "options": {
        "baseURL": "https://api.fireworks.ai/inference/v1",
        "apiKey": "{env:FIREWORKS_API_KEY}",
    },
},
```

And the model entry:

```python
"fireworks": "fireworks/accounts/fireworks/routers/kimi-k2p5-turbo",
```

Add `fireworks` to `_PREFERENCE_ORDER` *before* `anthropic` (so it's the
default when present — that's the whole point of this run).

**Risk**: OpenCode's provider format may not handle slashes in model IDs
cleanly. If it chokes, fall back to declaring an explicit `models` block
in the provider entry. Verifiable from inside the sandbox by running
`opencode --version` then checking what model it picks.

## Step 3 — Create the credential binding via SDK

This is the broker path — the secret never touches the repo.

```python
import asyncio, os
from omoios import AsyncOmoiOSClient

async def main():
    async with AsyncOmoiOSClient(
        base_url=os.environ["OMOIOS_API_BASE_URL"],
        api_key=os.environ["OMOIOS_PLATFORM_API_KEY"],
    ) as c:
        binding = await c.credentials.create(
            workspace_id=os.environ["OMOIOS_TEST_WORKSPACE_A"],
            kind="bearer_secret",
            name="fireworks-kimi",
            value=os.environ["FIREWORKS_API_KEY"],
        )
        print(f"binding_id={binding.id}")

asyncio.run(main())
```

## Step 4 — Create an EnvironmentVersion bound to that credential

There's no SDK method for environment-version yet (we have
`environments` resource). The CLI for this should ship in next
iteration — but for proof-of-life we can call the route directly:

```python
async with c as client:
    env = await c.environments.create(
        organization_id=ORG_ID,
        name="kimi-fireworks-poc",
    )
    # Direct POST until SDK gets envversion support:
    r = await client._request("POST",
        f"/api/v1/environments/{env.id}/versions",
        json={
            "image": "nikolaik/python-nodejs:python3.12-nodejs22",
            "credentials": {
                "fireworks": {
                    "kind": "bearer_secret",
                    "binding_id": binding.id,
                }
            },
        }
    )
    env_version_id = r.json()["id"]
```

The credential alias `fireworks` is what the bootstrap reads to render
auth.json. The renderer (step 2) maps that alias to the OpenCode
provider config, which uses `{env:FIREWORKS_API_KEY}` — but inside the
sandbox the bootstrap actually rewrites this from the broker fetch (see
`sandbox/bootstrap.sh:render_auth_entry`).

**Spec subtlety**: the bootstrap renders auth.json from broker data, NOT
from env vars. OpenCode reads `auth.json` for keys regardless of what
opencode.json says about `{env:FIREWORKS_API_KEY}`. So as long as
`fireworks` is in `auth.json`, the LLM call works. Verify by exec'ing
`cat ~/.local/share/opencode/auth.json` inside the sandbox — should show
`{"fireworks": {"type": "api", "key": "Fw_..."}}`.

## Step 5 — Spawn the session with a real prompt

```python
session = await c.sessions.create(
    workspace_id=os.environ["OMOIOS_TEST_WORKSPACE_A"],
    environment_id=env.id,
    prompt="Explain in 3 bullets how OpenCode finds its provider keys.",
    metadata={"source": "proof-of-life-2026-04-26"},
)
print(f"session_id={session.id}")
```

## Step 6 — Stream events and watch the trajectory

```python
async for evt in c.sessions.events(session.id):
    print(f"  seq={evt.seq:>3} {evt.type:<24} actor={evt.actor}")
    if evt.type in ("session.succeeded", "session.failed", "session.cancelled"):
        print(f"\nTERMINAL: {evt.type}")
        break
```

What we expect to see, in order:
1. `session.created` — actor=user
2. `session.started` — actor=agent (orchestrator picked up + sandbox spawned)
3. `session.message` events from `actor=agent` carrying the LLM output
   chunks (token-by-token if streaming is wired) or full text
4. `session.succeeded` — actor=system

If we see `session.failed` or `session.cancelled`, capture the
`error_message` and the last few events for triage.

## Step 7 — Pull artifacts (if any)

```python
artifacts = await c.sessions.artifacts(session.id)
for a in artifacts:
    print(f"  {a.name} ({a.size_bytes} bytes, {a.content_type})")
```

For a pure-text response, OpenCode may or may not write an artifact —
the `session.message` events should already contain the answer. Artifact
verification is a bonus check, not a gate.

## Step 8 — Hardening before the next session

A single proof-of-life run validates the path. Before relying on it,
fix anything that the run exposed:

- If OpenCode rejects `fireworks/accounts/...` model IDs → patch the
  renderer's model formatter
- If bootstrap doesn't run → either invoke it via `sb.exec` post-spawn
  (Modal) or move auth.json render into the spawner directly (mirrors
  what we already did for opencode.json)
- If the orchestrator picks up the session but never spawns a sandbox →
  trace through `orchestrator_worker.py` claim → spawn path; likely
  related to the spawner factory not seeing `SANDBOX_PROVIDER=modal`
- If the agent runs but takes >10min → likely Modal cold start; bake
  OpenCode + OmO into the image rather than relying on the bootstrap
  to install them

## Hand-off package for next session

This file is the input. Next session should:

1. Confirm orchestrator + smoke account are still live (ScheduleWakeup
   usually keeps them warm; if not, re-run `setup_prod_smoke_account.py`)
2. Set `FIREWORKS_API_KEY` on Railway
3. Land the renderer patch from step 2 + push
4. Run a single Python script that does steps 3-7 in sequence
5. Capture the event stream + final status to
   `.sisyphus/evidence/agent-proof-of-life-<date>.json`
6. Whatever fails, iterate from step 8

## Spec reference

- spec §3 sessions API (create / events / cancel / reply)
- spec §4 broker (credential alias delivery to sandbox)
- spec §5 environment versions (immutable credential binding)
- spec §14 OmO config schema
- spec §18 §3 primitive patterns (this is Pattern B — sync wait)

## Discipline notes (from the user)

- **Terminal first, UIs second.** Provider mgmt + GitHub auth + onboarding
  must work as CLI flows before anyone builds a frontend page for them.
  This proof-of-life script is itself the first such CLI.
- **Bare minimum is shipped.** Resist building extras (Slack bot, Chrome
  extension, voice, etc.) until the agent loop has been observed end-to-
  end at least once. Stuff built on top of an unobserved loop is built on
  faith.
