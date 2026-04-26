# 17 · omoi_os Adaptation Guide

You already have most of what the spec describes. This document maps what you have to what the spec calls it, identifies the real gaps, and sequences the refactor incrementally — no rewrite, no abandoning FastAPI, no throwing away billing code.

**Architectural premise:** you already have Next.js dashboard + FastAPI backend. The spec describes exactly this topology, just with different names. Your job isn't to rebuild — it's to rename, extend, and add the specific pieces you don't have.

## 1 · Start with an honest audit

Before doing any work, spend one hour answering these about `omoi_os`. This is the cheapest step and the most valuable — it prevents rebuilding things you already have.

### A · Domain model
- [ ] What's your top-level billing boundary? (Almost certainly = spec's `Organization`.)
- [ ] Do you have a workspace / project / repo-group concept between org and task? (= spec's `Workspace`.)
- [ ] What's the shape of a "task"? Fields, state machine, relationships.
- [ ] Does a task have events/messages/outputs, or is output a single final artifact?
- [ ] How are PRs / files / logs currently represented? (= spec's `Artifact`.)

### B · Auth
- [ ] What's issuing API keys today? (Your own? fastapi-users? A library?)
- [ ] What's the token format? (Raw string? JWT? HMAC-signed?)
- [ ] Is there a distinction between "tenant's server credential" and "end-user's session credential"? (Spec calls these platform key vs user JWT.)
- [ ] Is there anything currently playing the role of a short-lived, sandbox-scoped credential? (Spec's `sess_tok_…`.)
- [ ] What's the GitHub OAuth integration storing? (Per-user access tokens? Per-org?)
- [ ] Is there RBAC inside an org (owner/admin/member roles)? What's the enforcement layer?

### C · Sandbox and agent
- [ ] How does a task currently go from "user created it" → "agent running in Daytona"? Walk the code path.
- [ ] Where are provider API keys (Anthropic/OpenAI) stored and how are they injected into the sandbox?
- [ ] How does the agent send progress back? (WebSocket? SSE? DB polling?)
- [ ] Is there already a retry / fallback path when a model errors?

### D · Frontend
- [ ] Does the Next.js dashboard do auth itself or delegate to FastAPI?
- [ ] How does the dashboard stream live task state? (Which protocol?)
- [ ] Is there already a public SDK, or do customers only hit REST directly?

The answers determine how much of what follows you need to do.

## 2 · Name mapping

Most of what the spec calls new things are things you already have. Rename in your head, not necessarily in code (renaming DB tables with live billing is risky — keep the old names internally if needed).

| Spec term | Likely omoi_os term | Notes |
|---|---|---|
| `Organization` (`org_…`) | Org / Team / Account | The billing boundary. Almost certainly 1:1. |
| `Workspace` (`ws_…`) | Project / Workspace / Repo | If you don't have one: spec uses it optionally; skip for now. |
| `Environment` (`env_…`) | Probably doesn't exist as first-class | You likely have "task config" or "sandbox template" ad-hoc. First real addition. |
| `Session` (`sess_…`) | **Task** | Your main rename. State machine should already match. |
| `Artifact` (`art_…`) | Task output / PR / result | Check: is this first-class or embedded in the task row? |
| Platform API key (`rpk_live_…`) | Your existing API key | Rename prefix eventually; not urgent. |
| User JWT | Dashboard auth token | Whatever your Next.js → FastAPI auth flow produces. |
| Session token (`sess_tok_…`) | **Probably doesn't exist** | New capability — see §5. |

**Renaming strategy:** don't do a big-bang rename. Add new names as aliases in the API layer, keep old names in the DB. A `task_id` column can answer to both `task_id` and `session_id` at the API level via a serializer. Migrate the DB column name much later, or never.

## 3 · The gap list

After the audit, these are the things that are almost certainly new work regardless of what you find:

**Definitely new — direct additions to FastAPI:**
1. **`Environment` resource.** First-class entity with versioning, egress allowlist, image reference. Today your task probably embeds this ad-hoc.
2. **Session token mechanism.** A short-lived credential minted per-task that the sandbox presents to a Credential Broker. (§5 below.)
3. **Credential Broker endpoints.** The service sandboxes call to get ephemeral provider tokens.
4. **Three binding kinds** for credentials: `github_app`, `user_oauth`, `bearer_secret`. You probably already have Model A (`user_oauth` for GitHub); the other two are new.
5. **Hostname-level egress enforcement.** Daytona gives you network controls; Modal gives you CIDR allowlists. Neither does hostnames. You need an HTTP proxy in-sandbox.

**Probably new — depending on your current state:**
6. **Modal adapter.** When you migrate from Daytona.
7. **OpenCode adapter.** When you migrate from Claude Code.
8. **Event envelope standardization.** If your current events are ad-hoc per endpoint, normalize to `{ id, seq, type, actor, timestamp, data }`.
9. **Public SDK.** If customers currently hit raw REST, the SDK is a new deliverable. Auto-generate from OpenAPI.
10. **Better Auth integration.** **See §6 for the honest answer on whether to bother.**

**Not new — keep what you have:**
- Billing. Don't touch it unless the spec's concepts force a change (they mostly don't).
- Org model. Whatever's there is fine.
- GitHub user-OAuth. If it works, it's Model A from the spec — leave it alone.
- Next.js dashboard. It already talks REST to FastAPI; that's exactly what the spec wants.

## 4 · The task → session refactor (the cheap way)

Since the shape is already session-like, this is almost entirely an API-surface rename plus a few field additions. DB stays mostly put.

**Step 1 — Alias at the API layer.** Add session-named routes that proxy to your task routes:

```python
# routers/sessions.py — NEW file, thin adapter
from fastapi import APIRouter
from .tasks import (
    create_task, get_task, cancel_task, list_tasks,
    stream_task_events, reply_to_task, fork_task,
)

router = APIRouter(prefix="/v1/organizations/{org_id}/sessions")

# Each route delegates to the existing task handler.
# Response serializer renames task_id → id, adds any missing spec fields.

@router.post("")
async def create_session(org_id: str, body: CreateSessionRequest, ...):
    task = await create_task(org_id, body.to_task_params(), ...)
    return SessionResponse.from_task(task)

@router.get("/{session_id}")
async def get_session(org_id: str, session_id: str, ...):
    task = await get_task(org_id, task_id=session_id, ...)
    return SessionResponse.from_task(task)

# ... cancel, fork, events, etc.
```

Mount both routers. Old `/v1/.../tasks/*` stays for existing clients; new `/v1/.../sessions/*` is the public spec-compliant surface. Deprecate the old ones on your own schedule.

**Step 2 — Add missing fields to `SessionResponse`.** Anything in spec [`02 §Session`](./02-resources.md#session--sess_) that you don't currently return: `environment_version`, `acl`, `urls.events_sse / websocket / editor`, `usage.compute_seconds / tokens_input / tokens_output`. Some may be derivable from existing data; some require new columns.

**Step 3 — Normalize event envelope.** If your task events are ad-hoc, wrap them:

```python
# The shape you want (spec §03):
{
  "id":         "evt_01HW…",
  "seq":        142,
  "type":       "tool_call",
  "session_id": "sess_9Qw2",
  "actor":      "agent",
  "timestamp":  "2026-04-21T14:03:22.481Z",
  "data":       { ... whatever your task events already carry }
}
```

Add a tiny wrapper at emit time. Store `seq` monotonic per task. Existing consumers that don't care about the envelope can read `data`; new consumers get the full spec shape.

**What DOES NOT need to change:**
- The `tasks` DB table name.
- Any existing billing/metering that counts tasks. (Counts sessions identically — same rows.)
- Internal service code that uses `task` vocabulary. Rename on your own pace.

## 5 · The Credential Broker — the one non-trivial addition

This is the biggest piece you don't have. Walk through from scratch:

**New concept:** a `session_token` (short-lived, task-scoped API key) issued when a task starts, injected into the sandbox as `SESSION_TOKEN` env var. When the sandbox needs an LLM provider key, GitHub token, etc., it calls your Broker with this token; the Broker returns a scoped ephemeral credential.

**What this replaces:** however you currently inject provider keys into sandboxes. Probably one of:
- Static env vars set on sandbox creation (= leaks if the sandbox is compromised, long-lived)
- Secrets mounted from your FastAPI side (= OK for platform-level keys, not OK for per-user GitHub)

**The minimum viable Broker in FastAPI:**

```python
# routers/broker.py
from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/broker")

@router.get("/creds/{provider}")
async def mint_credential(
    provider: str,
    authorization: str = Header(...),
):
    # 1. Verify the session token. This is just your existing API key
    #    verification, with a short-TTL token type.
    session_token = authorization.removeprefix("Bearer ")
    session = await verify_session_token(session_token)
    if not session:
        raise HTTPException(403)

    org_id = session["org_id"]
    task_id = session["task_id"]
    task = await get_task(task_id)
    env = await get_environment_version(task["environment_id"], task["environment_version"])

    # 2. Check the environment declared this provider.
    binding = env["credentials"].get(provider)
    if not binding:
        raise HTTPException(404, "provider not declared in environment")

    # 3. Dispatch by binding kind.
    if binding["kind"] == "bearer_secret":
        # Your existing secret-lookup code. 90% case for LLM providers.
        secret = await get_secret(org_id, binding["secret_id"])
        return { "token": decrypt(secret.value), "expires_at": None, "scope": provider }

    if binding["kind"] == "user_oauth":
        # Your existing GitHub OAuth token fetch + refresh. Model A.
        # For GitHub, this is your existing flow.
        token = await get_user_oauth_token(task["created_by"], binding["provider"])
        return { "token": token.access_token, "expires_at": token.expires_at, "scope": binding["scope"] }

    if binding["kind"] == "github_app":
        # Model B: mint installation token. New code.
        return await mint_github_app_token(org_id, repos=binding["repositories"])

    raise HTTPException(500, f"unknown binding: {binding['kind']}")
```

That's the whole Broker. ~50 lines of FastAPI. You're probably doing most of the underlying work already (OAuth token fetch, secret decryption) — the Broker just routes between them based on an `env.credentials` declaration.

The new piece is `session_token` issuance. Minimal approach:

```python
# When a task is created:
async def create_task(org_id: str, ...):
    task = await db.tasks.insert({ ... })

    # Mint a short-lived API key bound to this task.
    # Reuse your existing API key system; add a new token type.
    session_token = await issue_api_key(
        org_id=org_id,
        kind="session",            # new enum value
        subject_id=task.id,
        ttl_seconds=3600,
        metadata={ "task_id": task.id, "environment_id": task.environment_id },
    )

    # Inject into sandbox env at boot.
    await provision_sandbox(task, extra_env={ "SESSION_TOKEN": session_token.plaintext })

    return task
```

The verification path (`verify_session_token` above) is whatever your existing API key verification is, filtered to `kind=session`.

## 6 · Better Auth — the honest answer

**You probably don't want it.** Here's why:

Better Auth's value in the greenfield spec was:
- Ready-made organization/team model (`organization` plugin)
- Ready-made API key system (`apiKey` plugin)
- Ready-made JWT + JWKS (`jwt` plugin)
- Ready-made OAuth linking + auto-refresh (`socialProviders`)

**You already have all of these.** Billing works on your org model; your API keys work; your GitHub OAuth works. The spec's "Better Auth integration" doc is 25KB of "here's how to build these things from scratch in a new codebase." You've already paid that cost.

Ripping out your existing auth to replace with Better Auth would be a rewrite that gains you nothing except consistency with a spec that exists to help greenfield builders.

**What you should actually do:**

1. **Audit your current auth against the spec's three-token model** (`rpk_live_…` platform key, `eyJ…` user JWT, `sess_tok_…` session token). You probably have the first two (maybe with different names). You're adding the third (§5).
2. **Normalize the middleware** so every route produces a uniform `AuthContext` regardless of which token type got them there. See [`13 §9`](./13-better-auth-integration.md) — this is the one pattern worth stealing from the Better Auth doc, and it's 30 lines of Python.
3. **If your Next.js dashboard auth is fragile** (most hand-rolled auth eventually gets there), consider migrating *only the dashboard* to Better Auth later. Your FastAPI backend doesn't need to change; it just needs to verify the JWTs Better Auth issues. This is a future-proofing move, not a now move.

The spec's `13-better-auth-integration.md` stays in the project as "if we ever greenfield a new service, here's the pattern." It does not stay as "refactor omoi_os to match this."

## 7 · Daytona → Modal migration

Keep this decoupled from everything else. Define an adapter interface and swap implementations; don't do it during the same PR as the task→session rename.

```python
# sandbox/protocol.py
from typing import Protocol, AsyncIterator

class SandboxProvider(Protocol):
    async def create(self, spec: SandboxSpec) -> Sandbox: ...
    async def exec(self, sandbox_id: str, cmd: list[str]) -> AsyncIterator[bytes]: ...
    async def write_file(self, sandbox_id: str, path: str, content: bytes) -> None: ...
    async def read_file(self, sandbox_id: str, path: str) -> bytes: ...
    async def expose_port(self, sandbox_id: str, port: int) -> str: ...  # returns URL
    async def terminate(self, sandbox_id: str) -> None: ...
    async def wait(self, sandbox_id: str) -> int: ...

# sandbox/daytona.py — your current code, behind the interface
class DaytonaProvider: ...

# sandbox/modal.py — new, parallel implementation
class ModalProvider: ...

# sandbox/__init__.py
provider: SandboxProvider = ModalProvider() if settings.SANDBOX == "modal" else DaytonaProvider()
```

Switch via env flag. Run both in parallel on non-production workloads before flipping. The adapter boundary should be where all sandbox operations go through — so the rest of your code doesn't care which provider is underneath.

Modal's Python SDK is mature; most of what [`15`](./15-modal-integration.md) says about the TS SDK's limitations doesn't apply to you. You get `Image.debian_slim().apt_install().pip_install()`, snapshot-restore, everything. The TS SDK gap is somebody else's problem.

## 8 · Claude Code → OpenCode migration

Same pattern as Daytona → Modal. Define an interface, swap implementations. See [`14`](./14-omo-opencode-sandbox.md) for the OpenCode-specific config model. Key points for your case:

- OpenCode reads `~/.local/share/opencode/auth.json` for provider creds — your Broker can write this file into the sandbox at boot instead of (or in addition to) env vars.
- OpenCode's config is per-sandbox, so no shared state to worry about.
- OmO layered on top gives you multi-agent + fallback chains, but only if you want it. You can start with plain OpenCode + one model per task, add OmO later.

## 9 · The migration sequence

One PR per item, in this order:

1. **Audit (1 hour).** Fill in §1 above. Know what you have before changing anything.
2. **Adapter interfaces for sandbox + agent (1 day).** Refactor current Daytona + Claude Code code behind protocols. No behavior change. Unblocks both migrations.
3. **Session API surface (1–2 days).** Add `/v1/organizations/{org}/sessions/*` routes as aliases over tasks. Add missing response fields. Normalize event envelope. Tasks-side API stays working.
4. **Credential Broker (2–3 days).** `/broker/creds/{provider}` endpoint. Session token issuance on task create. Update sandbox bootstrap to use `SESSION_TOKEN` instead of direct env injection.
5. **`Environment` resource (2–3 days).** First-class entity with versioning, egress allowlist, credentials map. Migrate existing ad-hoc per-task config into reusable environments. This is the biggest genuinely new thing.
6. **Modal migration (1 week, parallel to production).** Implement `ModalProvider`. Test in staging. Flip flag for one tenant, then all.
7. **OpenCode migration (3–5 days).** Implement `OpenCodeAgent`. Same pattern.
8. **Public SDK (2–3 days).** Auto-generate from OpenAPI. FastAPI already emits good specs; Python + TS clients fall out of `openapi-generator`.
9. **Client surfaces (Slack / CI / Chrome extension).** Each is independent; add as product priorities dictate.

**What's NOT on this list:**
- Better Auth migration. Skip unless you hit a specific limit with current auth.
- Task → session DB rename. API alias is enough; rename the DB table never or during a scheduled migration window.
- Rewriting billing. Nothing in the spec forces changes here.
- Monorepo restructuring. If omoi_os has a layout that works, leave it alone.

## 10 · What the spec is actually for, for you

Not a rewrite target. A **checklist and vocabulary**:

- **Checklist:** what capabilities should a mature agent platform have? Read the spec; tick off what omoi_os has; the unticked items are your roadmap.
- **Vocabulary:** when you're documenting omoi_os for users, use the spec's names (session, environment, artifact, platform API key). They're more accurate and more portable than internal names that accreted as the codebase grew.
- **Reference for the hard parts:** the Credential Broker design ([`13 §8`](./13-better-auth-integration.md)), the OmO fallback chain configuration ([`14`](./14-omo-opencode-sandbox.md)), the egress model ([`05`](./05-environments.md)), the event envelope ([`03`](./03-sessions-api.md)) — these are worth reading closely because they're the things you're most likely to get subtly wrong on your first pass.

Most of the rest is "how you'd build this from scratch" — not relevant to you. Skim for ideas; don't follow literally.

## 11 · Three next steps

1. **Do the §1 audit today.** Takes an hour; eliminates 80% of the uncertainty about the rest. Before writing any code, know what you already have.
2. **Ship the adapter interfaces first (step 2 in §9).** Both migrations (Daytona→Modal, Claude Code→OpenCode) depend on this, and it's risk-free — pure refactor, no behavior change. Highest-leverage single PR on the list.
3. **Draft the `Environment` schema in your head before you write code for it.** It's the one resource you're genuinely adding from scratch, and getting its shape right (especially the `credentials` map with the three binding kinds) is the foundation for the Broker. Spend an hour designing before typing.

## Reflective question

The spec was written for someone starting from zero. You're starting from a working SaaS with real customers — or at least real infrastructure. **The risk isn't that you'll do too little; it's that you'll do too much.**

Specifically: there's a version of this where you audit, decide to adopt 40% of the spec, and ship in six weeks. There's another version where you get excited about Better Auth or TypeScript or monorepo aesthetics and spend four months rewriting things that already work, for no customer-visible gain.

**Which version are you more likely to drift toward?** If you're honest about the answer, you can design against it. The spec is genuinely useful as a reference. It's genuinely dangerous as a rewrite target for a working system.
