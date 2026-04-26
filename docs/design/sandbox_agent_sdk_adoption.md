# sandbox-agent-sdk Adoption — Handoff & Plan

**Created:** 2026-04-26
**Status:** Phase 1 paused at Task #7 — agent-strategy pivot needed
**Purpose:** Hand off the in-flight SDK adoption work, document the live-test pivot away from ACP, and lay out the revised remaining plan.

---

## TL;DR

- 6 of 8 phase-1 tasks complete; both feature branches pushed; 67 new tests green.
- Live Modal smoke validates **spawn + interact** end-to-end against real Modal.
- **Task #7 pivot**: stop trying to put opencode behind the SDK's ACP/sandbox-agent server (it doesn't register opencode as an agent type). Instead, spawn `opencode serve` directly in the Modal sandbox and drive it with `AsyncOpencode` — the proven Daytona-chat pattern. Keep the SDK's `SandboxProvider` abstraction and the `SessionPersistDriver` adapter; drop the SDK's `SandboxAgent` client and `Session` abstraction from the chat path.

---

## Branches & PRs

| Repo | Branch | Commits | PR URL |
|---|---|---|---|
| `kivo360/sandbox-agent-python` | `feat/persistence-driver-injection` | 4 | [open PR](https://github.com/kivo360/sandbox-agent-python/pull/new/feat/persistence-driver-injection) |
| `kivo360/OmoiOS` | `feat/sandbox-agent-sdk-adoption` | 5 | [open PR](https://github.com/kivo360/OmoiOS/pull/new/feat/sandbox-agent-sdk-adoption) |

### sandbox-agent-python commits

| SHA | What |
|---|---|
| `234de41` | `SessionPersistDriver` Protocol + `persistence=` kwarg on `SandboxAgent.__init__/connect/start`. Bumped 0.1.5 → 0.2.0. |
| `0e731ca` | Widen `websockets` constraint to `<16` so omoi_os daytona dep resolves. |
| `bcdbcbe` | Rewrite `providers/modal.py` against the real Modal SDK (`modal.App.lookup`, `modal.Sandbox.create/from_id`, `modal.Image.from_registry`, `modal.Secret.from_dict`). Previous code referenced `modal.ModalClient` / `modal.SandboxCreateParams` which don't exist. |
| `0d1dbf1` | Track `self.sandbox_id` on the provider, switch to native `.aio()` async API, fix `memory_mib`→`memory` kwarg name (Modal's actual param). |

### omoi_os commits

| SHA | What |
|---|---|
| `926806e2` | `OmoiOsSessionPersistDriver` adapter over existing `tasks` + `events` tables (no parallel schema). 33 unit tests. |
| `8ae62776` | `OmoiOsModalProvider` — thin subclass of SDK `ModalProvider` with omoi_os defaults (app name, memory, timeout) and an `image` builder for sandbox-agent + opencode. 17 unit tests. |
| `ae52d249` | Pause-state working buffer for PR review. |
| `61784696` | Five live-Modal probe scripts under `scripts/poof/`. `build_omoi_modal_image()` switched from broken `rivetdev/sandbox-agent` registry image to a self-built `debian_slim`-based image. |

---

## Tasks

| # | Subject | Status | Notes |
|---|---|---|---|
| 1 | SDK Protocol + persistence injection | ✅ done | Branch above. |
| 2 | omoi_os pin sandbox-agent-sdk 0.2.0 | ✅ done | Editable local path until publish. |
| 3 | Alembic migration | ❌ deleted | Existing tables fully cover SDK shape. |
| 4 | `OmoiOsSessionPersistDriver` adapter | ✅ done | 33 unit tests. |
| 5 | `OmoiOsModalProvider` subclass | ✅ done | 17 unit tests. |
| 6 | Bake sandbox-agent + opencode into Modal image | ✅ rolled into #5 | `build_omoi_modal_image()`. |
| 7 | Replace `_dispatch_to_sandboxed_agent` in chat_responder | 🚧 BLOCKED | Pivot needed (this doc). |
| 8 | Smoke probe + DB-backed integration tests | ⏳ pending | After #7. |

---

## Live Validation Findings (2026-04-26 evening)

Five probe scripts under `scripts/poof/`:

| Probe | Status | What it shows |
|---|---|---|
| `probe_sdk_modal_simple.py` | PASS | Plain `debian_slim` sandbox + exec: validates Modal API + asyncio.to_thread plumbing. |
| `probe_sdk_install.py` | PASS | `curl -fsSL $SANDBOX_AGENT_INSTALL_SCRIPT \| sh` lands a working `sandbox-agent` binary on a fresh `debian_slim`. |
| `probe_sdk_modal_diagnose.py` | FAIL (expected) | The `rivetdev/sandbox-agent:0.5.0-rc.2-full` registry image kills the sandbox immediately on `Sandbox.create("sleep","infinity",...)` because its ENTRYPOINT swallows our args. |
| `probe_sdk_modal_spawn.py` | PASS | Full happy path: `OmoiOsModalProvider().create()` → `get_url()` → HTTP `GET /v1/health` returns `{"status":"ok"}` → `GET /v1/agents` returns the agent registry → `destroy()` clean. |
| `probe_sdk_modal_session.py` | FAIL | `agent.create_session(agent="opencode")` returns `AcpHttpError: Invalid Request` because opencode is not a registered ACP agent in sandbox-agent server. |

### Bugs caught and fixed inline

1. SDK `providers/modal.py` referenced `modal.ModalClient` and `modal.SandboxCreateParams` — neither exists in any modal release. Rewritten against real API.
2. SDK provider used `memory_mib=` — Modal's actual kwarg is `memory=`. Aliased `memory_mib` in `create_opts` for explicit unit naming, translated at the call site.
3. SDK provider didn't track `self.sandbox_id` so `agent.sandbox_id` (which delegates to provider) raised `AttributeError`. Now set in `create()`.
4. SDK provider's `asyncio.to_thread` wrappers triggered Modal `AsyncUsageWarning`. Replaced with native `.aio()` variants.
5. `rivetdev/sandbox-agent:0.5.0-rc.2-full` image is unusable as a Modal base because its ENTRYPOINT clobbers `Sandbox.create` args. Switched omoi_os image to `debian_slim` + install scripts.

---

## The Real Blocker — and the Pivot

### What didn't work

Phase-1 plan was: SDK's `SandboxAgent.start(provider=…)` runs `sandbox-agent server` inside the Modal sandbox; ACP routes `session.prompt` calls to a registered agent like opencode.

What actually happens: sandbox-agent server's agent registry only knows the agents in `SDK providers/shared.py:7 DEFAULT_AGENTS = ["claude", "codex"]`. There is no built-in opencode ACP adapter. `agent.create_session(agent="opencode")` returns 400 Invalid Request.

### Why the pivot is right

The existing **Daytona-chat path already runs `opencode serve` directly** as the sandbox's HTTP server — no ACP, no sandbox-agent server in the middle. See `backend/omoi_os/services/sandboxed_agent.py:434`:

```python
f"nohup opencode serve --port {port} --hostname 0.0.0.0 ..."
```

And clients drive it with the native opencode Python client:

```python
from opencode_ai import AsyncOpencode
client = AsyncOpencode(base_url=preview_url)
resp = await client.session.prompt(id=opencode_session_id, ...)
```

This is proven, has session continuity across turns, and doesn't depend on the ACP layer.

### The pivot (Task #7 revised)

| Component | Phase-1 plan (broken) | Phase-1 revised (pivot) |
|---|---|---|
| Sandbox lifecycle | SDK `SandboxProvider` ✓ | SDK `SandboxProvider` ✓ (kept) |
| Image | `debian_slim` + sandbox-agent + opencode | `debian_slim` + opencode (drop sandbox-agent) |
| Sandbox entrypoint | `sandbox-agent server --no-token --port 3000` | `opencode serve --port {port} --hostname 0.0.0.0` |
| Tunnel URL | sandbox-agent's HTTP API | opencode's HTTP API |
| Chat client | SDK `SandboxAgent` + `Session` (ACP) | `AsyncOpencode(base_url=...)` |
| Session persistence | `OmoiOsSessionPersistDriver` | `OmoiOsSessionPersistDriver` (kept — translates events) |
| Cross-replica re-attach | `provider.reconnect()` (`from_id`) | `provider.reconnect()` (`from_id`) (kept) |

### What we keep from the SDK adoption

- ✅ `SandboxProvider` abstraction (sandbox-agent-python `providers/types.py`) — clean lifecycle interface
- ✅ `OmoiOsModalProvider` (omoi_os `services/sa_modal_provider.py`) — but change the entrypoint (see below)
- ✅ `SessionPersistDriver` Protocol (sandbox-agent-python `persistence.py`) — interface contract still useful
- ✅ `OmoiOsSessionPersistDriver` adapter (omoi_os `services/agent_session_persist.py`) — session/event translation layer

### What we drop from the SDK adoption (chat path only)

- ❌ `SandboxAgent` class in chat path — not useful when we're not using ACP
- ❌ SDK `Session` abstraction — opencode has its own session model
- ❌ ACP / sandbox-agent server inside the Modal sandbox — unnecessary middleware
- ❌ `WorkspaceConfig.auth_json` / `_bootstrap_workspace` — opencode reads `~/.local/share/opencode/auth.json` directly; we write it via `sandbox.exec` like the Daytona path does

These could come back later for SDK-direct sessions or other workloads, but phase-1 chat doesn't need them.

---

## Concrete Remaining Work (Task #7, revised)

### 1. Update `OmoiOsModalProvider` to spawn opencode serve

File: `backend/omoi_os/services/sa_modal_provider.py`

Override `create()` (don't inherit from base) so the entrypoint is opencode serve:

```python
sandbox = await modal.Sandbox.create.aio(
    "sh", "-c",
    f"/root/.opencode/bin/opencode serve --port {self.agent_port} --hostname 0.0.0.0",
    app=app,
    image=image,
    secrets=secrets,
    encrypted_ports=[self.agent_port, *extra_ports],
    memory=memory,
    timeout=timeout,
)
```

Default `agent_port` becomes 4096 (opencode's default) instead of 3000 (sandbox-agent server's default).

### 2. Simplify `build_omoi_modal_image()`

Drop the sandbox-agent install line — only opencode is needed:

```python
img = modal.Image.debian_slim().apt_install("curl", "ca-certificates", "git")
return img.run_commands(
    "mkdir -p /root/.local/share/opencode /root/.config/opencode",
    "chmod 700 /root/.local/share/opencode",
    "curl -fsSL https://opencode.ai/install | bash",
    "/root/.opencode/bin/opencode --version",
)
```

### 3. Build `OmoiOsSandboxedAgentModal`

New file: `backend/omoi_os/services/sandboxed_agent_modal.py`

Mirrors the existing `services/sandboxed_agent.py` (Daytona) but uses `OmoiOsModalProvider` for sandbox lifecycle. One runtime class per provider per the existing design principle.

Class shape (mirror Daytona):
```python
@dataclass
class ModalSandboxedAgent:
    sandbox_id: str
    sandbox: Any            # modal.Sandbox handle
    preview_url: str
    opencode_session_id: str
    _client: AsyncOpencode | None = None

    async def prompt(self, text: str) -> str:
        client = self._client or AsyncOpencode(base_url=self.preview_url)
        resp = await client.session.prompt(id=self.opencode_session_id, ...)
        return resp.text

    async def close(self) -> None:
        # destroy sandbox via provider
        ...
```

Same `get_or_spawn(session_id)` API as Daytona — checks in-process cache → DB rehydrate via `task.result['sandbox_agent']` → fresh spawn via `OmoiOsModalProvider.create()`.

### 4. Wire `_dispatch_to_sandboxed_agent`

File: `backend/omoi_os/services/chat_responder.py:268-299`

When `sandbox.provider == "modal"`, route to `sandboxed_agent_modal.get_or_spawn(session_id)` instead of the old `modal_sandboxed_agent.get_or_spawn`. Same shape as the Daytona branch.

Delete `backend/omoi_os/services/modal_sandboxed_agent.py` (the old single-shot stdout-scraping path).

### 5. Persist driver wiring

The `OmoiOsSessionPersistDriver` (already shipped) doesn't need changes for this pivot. The driver writes session events (entity_type='session', entity_id=task.id) regardless of which agent runtime emits them. chat_responder's existing `SessionEventEnvelope.emit` flow keeps working.

Future: if/when we adopt SDK-direct sessions, the persist driver becomes the bridge between SDK session events and omoi_os events table.

### 6. Tests

- Unit: `backend/tests/unit/services/test_sandboxed_agent_modal.py` — mirrors `test_sandboxed_agent.py` (Daytona). Mock `OmoiOsModalProvider`, mock `AsyncOpencode`, exercise `prompt`/`close`/`get_or_spawn` paths.
- Integration: `backend/tests/integration/test_sandboxed_agent_modal_live.py` — spawn real Modal sandbox via `OmoiOsModalProvider`, drive one opencode `session.prompt`, assert non-empty reply, tear down. Skipif missing `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET`/`LLM_API_KEY` (Fireworks key written into `auth.json` for opencode).
- Probe: `scripts/poof/probe_modal_chat_via_sdk.py` — full chat round-trip end-to-end.

---

## Decisions Still Open

1. **Does the SDK `SandboxAgent` client come back later?** Useful for SDK-direct sessions where consumers want the SDK's `Session` API. Phase 1 doesn't need it; revisit when we have a concrete SDK-direct consumer.

2. **Persist driver: keep, or trim?** Even without the SDK Session abstraction, the `SessionPersistDriver` shape gives downstream consumers a stable contract and a clean place to translate SDK-shaped events to the omoi_os events table. Recommend keeping it.

3. **Multi-runtime story.** Daytona-chat (`sandboxed_agent.py`) and Modal-chat (new `sandboxed_agent_modal.py`) are sibling runtimes — one class per provider per the design principle in memory. `_dispatch_to_sandboxed_agent` selects on `sandbox.provider`. If a third runtime arrives (local Docker → opencode), it follows the same shape.

4. **Does sandbox-agent server still get installed in the omoi_os image?** No — drop it. We're not using it in the chat path. If we later decide to expose ACP for some tooling integration, we add it back.

5. **opencode credential flow.** Daytona-chat path writes `auth.json` directly into the sandbox filesystem via `sandbox.process.exec`. Modal path should do the same via `sandbox.exec`. Don't use SDK's `WorkspaceConfig` for chat. Body shape: `{"fireworks-ai": {"type": "api", "key": settings.llm_api_key}}` (matches the proven 2026-04-26 runbook).

---

## Open Risks

1. **Modal sandbox tunnel + opencode.** Need to verify that `opencode serve --hostname 0.0.0.0` listens correctly under Modal's tunnel mapping. Daytona uses preview links; Modal uses tunnels. Should work but is unverified — run a probe before committing the chat-path code.

2. **opencode session continuity across turns.** Daytona path keeps `opencode_session_id` in `task.result['sandbox_agent']` and reuses across turns. Modal path needs the same — verify cross-replica rehydration via `modal.Sandbox.from_id()` still resolves the live opencode session inside the sandbox.

3. **Fireworks model alias.** Currently `OPENCODE_MODAL_MODEL` defaults to `fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo`. Verify this still resolves in the new path; the `auth.json` provider id must match (`fireworks-ai`).

4. **Cold-start latency.** Modal image build is one-time-cached but health-probe loop on opencode-serve may need tuning. Daytona path uses 60s polling; mirror that.

---

## Reference

- Working buffer: [`memory/working-buffer.md`](../../memory/working-buffer.md)
- Existing Daytona-chat path: `backend/omoi_os/services/sandboxed_agent.py`
- Existing Modal-chat (to delete): `backend/omoi_os/services/modal_sandboxed_agent.py`
- New persist driver: `backend/omoi_os/services/agent_session_persist.py`
- New Modal provider: `backend/omoi_os/services/sa_modal_provider.py`
- Probe scripts: `scripts/poof/probe_sdk_modal_*.py`, `probe_sdk_install.py`
- Auto-memory feedback rule: `feedback_reuse_existing_tables.md` — adapt to existing tables, don't add parallel schema for SDK adapters.
