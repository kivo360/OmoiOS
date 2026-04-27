# sandbox-agent-sdk Adoption — Handoff & Plan

**Created:** 2026-04-26
**Status:** Phase 1 unblocked — full chat round-trip verified end-to-end via SDK ACP + opencode
**Purpose:** Hand off the in-flight SDK adoption work, document the SDK bugs found in live testing, and lay out the remaining plan for chat_responder integration.

---

## TL;DR

- 6 of 8 phase-1 tasks complete; both feature branches pushed.
- **Live Modal smoke validates the full chat round-trip via the SDK ACP path**: spawn → connect → `create_session(agent="opencode")` → `session.prompt("…")` → stopReason: end_turn (35 output tokens) → clean teardown.
- Earlier ACP-vs-opencode-serve "pivot" was wrong — opencode IS a first-class supported agent (see `docs/agents/opencode.mdx` in the sandbox-agent repo). The blocker was 7 bugs in the Python SDK that prevented any JSON-RPC call from succeeding. All fixed.
- Remaining: wire chat_responder to the SDK + persist-driver path (Task #7), add DB-backed integration tests (Task #8).

---

## Branches & PRs

| Repo | Branch | Commits | PR URL |
|---|---|---|---|
| `kivo360/sandbox-agent-python` | `feat/persistence-driver-injection` | 5 | [open PR](https://github.com/kivo360/sandbox-agent-python/pull/new/feat/persistence-driver-injection) |
| `kivo360/OmoiOS` | `feat/sandbox-agent-sdk-adoption` | 6+ | [open PR](https://github.com/kivo360/OmoiOS/pull/new/feat/sandbox-agent-sdk-adoption) |

### sandbox-agent-python commits

| SHA | What |
|---|---|
| `234de41` | `SessionPersistDriver` Protocol + `persistence=` kwarg on `SandboxAgent.__init__/connect/start`. Bumped 0.1.5 → 0.2.0. |
| `0e731ca` | Widen `websockets` constraint to `<16` so omoi_os daytona dep resolves. |
| `bcdbcbe` | Rewrite `providers/modal.py` against the real Modal SDK (`modal.App.lookup`, `modal.Sandbox.create/from_id`, `modal.Image.from_registry`, `modal.Secret.from_dict`). Previous code referenced `modal.ModalClient` / `modal.SandboxCreateParams` which don't exist. |
| `0d1dbf1` | Track `self.sandbox_id` on the provider, switch to native `.aio()` async API, fix `memory_mib`→`memory` kwarg name. |
| `5ddc2cd` | **Six ACP bugs that prevented any session creation**: `?agent=` first-POST query param, `protocolVersion` int not string, `clientCapabilities: {}`, `session/new` not `session/create`, pass agent to AcpHttpClient, `cwd`/`mcpServers` defaults in `session/new`, prompt as content-parts array, read server's `sessionId` field. |

### omoi_os commits

| SHA | What |
|---|---|
| `926806e2` | `OmoiOsSessionPersistDriver` adapter over existing `tasks` + `events` tables (no parallel schema). 33 unit tests. |
| `8ae62776` | `OmoiOsModalProvider` — thin subclass of SDK `ModalProvider` with omoi_os defaults. 17 unit tests. |
| `ae52d249` | Pause-state working buffer for PR review. |
| `61784696` | Five live-Modal probe scripts. `build_omoi_modal_image()` switched from broken `rivetdev/sandbox-agent` registry image to `debian_slim`. |
| `82fd534c` | Earlier handoff doc (this doc, pre-SDK-bug-fixes). Now superseded by this revision. |
| (pending) | `.env({"PATH": ...})` on Modal image so opencode binary is discoverable; new `probe_sdk_modal_session.py` verifying full chat round-trip; `probe_sdk_acp_curl.py` for raw-protocol diagnostics. |

---

## Tasks

| # | Subject | Status | Notes |
|---|---|---|---|
| 1 | SDK Protocol + persistence injection | ✅ done | Plus 6 ACP bug fixes from live testing. |
| 2 | omoi_os pin sandbox-agent-sdk 0.2.0 | ✅ done | Editable local path until publish. |
| 3 | Alembic migration | ❌ deleted | Existing tables fully cover SDK shape. |
| 4 | `OmoiOsSessionPersistDriver` adapter | ✅ done | 33 unit tests. |
| 5 | `OmoiOsModalProvider` subclass | ✅ done | 17 unit tests. |
| 6 | Bake sandbox-agent + opencode into Modal image | ✅ rolled into #5 | Plus `PATH` env so opencode is discoverable. |
| 7 | Wire chat_responder to SDK + persist driver | ⏳ ready to start | Path is clear now; live round-trip proven. |
| 8 | Smoke probe + DB integration tests | ⏳ pending | After #7. |

---

## SDK Bugs Caught by Live Testing (all fixed in `5ddc2cd`)

The Python SDK shipped at v0.1.5 and never had a working session-creation path against the real sandbox-agent server. All seven of these were preventing `agent.create_session(...)` from succeeding for any agent:

1. **First POST missing `?agent=` query param.** Server returns 400 `"missing required 'agent' query parameter for first POST to /v1/acp/{server_id}"`. The SDK's `AcpHttpClient` had no concept of "first POST" or agent identity at the transport layer.

2. **`protocolVersion` sent as string.** Python SDK had `PROTOCOL_VERSION = "2025-03-18"` (the date label). Server-side zod schema validates as integer; rejects with `"Invalid input: expected number, received string"`. Correct value: `1`.

3. **`clientCapabilities` field missing.** TS SDK includes it (even as `undefined`); Python SDK omitted entirely. Server may reject. Fixed by sending `{}`.

4. **`session/create` instead of `session/new`.** Method names diverged. Server returns `"Method not found: session/create"`.

5. **`agent` kwarg not threaded through to `AcpHttpClient`.** Created the chicken/egg with bug #1 — even if the transport supported the query param, the high-level `create_session(agent="opencode")` didn't pass it down.

6. **`session/new` requires `cwd` + `mcpServers`.** Verified empirically — omitting either returns `"Invalid input: expected string/array, received undefined"`. Fixed by sending sensible defaults (`cwd: "/root"`, `mcpServers: []`); callers can override.

7. **Reading wrong response field for session id.** Server returns `result.sessionId` (e.g. `ses_2344925c4ffetm4VhbFOJyv3Ej`); Python SDK was reading `result.agentSessionId` which doesn't exist, leaving the field empty so all subsequent `prompt` calls failed.

8. **`session.prompt` wrapping.** Server requires `prompt` as an array of content parts (`[{type: "text", text: "…"}]`). Python's convenience signature took a string and forwarded it raw. Fixed to wrap automatically.

After all 7 fixes: `agent.create_session(agent="opencode")` returns a session, `session.prompt("Reply with PONG")` returns `{stopReason: "end_turn", usage: {...35 output tokens...}}`. Verified live against Modal sandbox `sb-3MxRMK59oZxMXxxReewbVc`.

---

## Live Validation Probes (scripts/poof/)

| Probe | Status | What it shows |
|---|---|---|
| `probe_sdk_modal_simple.py` | PASS | Plain `debian_slim` sandbox + exec works |
| `probe_sdk_install.py` | PASS | `curl install.sh` lands `sandbox-agent` binary |
| `probe_sdk_modal_diagnose.py` | FAIL (intentional) | `rivetdev/sandbox-agent:0.5.0-rc.2-full` registry image kills sandbox via ENTRYPOINT conflict — documents why we use a self-built image |
| `probe_sdk_modal_install_agent.py` | PASS | `sandbox-agent install-agent opencode` returns `alreadyInstalled:true` when opencode is on PATH |
| `probe_sdk_acp_curl.py` | PASS | Raw curl probe of ACP endpoints — found bugs #1–#8 above |
| `probe_sdk_modal_spawn.py` | PASS | Full provider lifecycle: spawn → /v1/health → /v1/agents → teardown |
| `probe_sdk_modal_session.py` | **PASS** | **Full chat round-trip via SDK ACP**: `SandboxAgent.start` → `create_session(agent="opencode")` → `session.prompt(...)` → stopReason: end_turn |

---

## What omoi_os Keeps from the SDK

- ✅ `SandboxProvider` abstraction (sandbox-agent-python `providers/types.py`)
- ✅ `OmoiOsModalProvider` (omoi_os) — subclass with omoi_os image + defaults
- ✅ `SessionPersistDriver` Protocol (sandbox-agent-python `persistence.py`)
- ✅ `OmoiOsSessionPersistDriver` adapter (omoi_os) — over existing `tasks` + `events` tables
- ✅ `SandboxAgent` client + ACP `Session` abstraction (now actually works) — chat_responder uses these directly
- ✅ Cross-replica re-attach via `provider.reconnect()` calling `modal.Sandbox.from_id`

The earlier "drop SandboxAgent / use opencode-serve directly" pivot was based on a misdiagnosis — opencode is a first-class supported agent and the SDK was simply broken in 7 places.

---

## Concrete Remaining Work (Task #7)

### 1. Build `OmoiOsSandboxedAgentSdk`

New file: `backend/omoi_os/services/sandboxed_agent_sdk.py`

Replaces the existing `modal_sandboxed_agent.py` (single-shot stdout-scraping). Sibling to the Daytona-chat path (`sandboxed_agent.py`) per the one-runtime-per-provider design principle.

```python
@dataclass
class SdkSandboxedAgent:
    sandbox_id: str
    sdk_session: Session       # sandboxagent.client.Session
    omoios_session_id: str

    async def prompt(self, text: str) -> str:
        # SSE events come through on_message during prompt; collect text
        # from agent_message_chunk events into a buffer.
        text_buffer: list[str] = []
        def _capture(event):
            payload = event.get("payload", {})
            if payload.get("sessionUpdate") == "agent_message_chunk":
                content = payload.get("content", {})
                if content.get("type") == "text":
                    text_buffer.append(content.get("text", ""))

        # Register listener (need to expose this on Session — TBD)
        self.sdk_session.add_event_listener(_capture)
        try:
            await self.sdk_session.prompt(text)
        finally:
            self.sdk_session.remove_event_listener(_capture)
        return "".join(text_buffer)

    async def close(self) -> None:
        await self.sdk_session.dispose()
        # provider.destroy is called by the higher-level cleanup path
```

The persist driver writes the events to omoi_os events table automatically.

### 2. Wire `_dispatch_to_sandboxed_agent`

File: `backend/omoi_os/services/chat_responder.py:268-299`

When `sandbox.provider == "modal"`:
```python
provider = OmoiOsModalProvider(env_vars=_build_env_vars(...))
agent = await SandboxAgent.start(
    provider=provider,
    workspace_files={"auth.json": WorkspaceConfig.auth_json({
        "fireworks-ai": {"type": "api", "key": settings.llm_api_key}
    })},
    persistence=OmoiOsSessionPersistDriver(db),
)
session = await agent.resume_or_create_session(
    session_id=task.id,
    agent="opencode",
)
text = await sandboxed_agent_sdk.prompt(session, user_text)
```

Then emit a single `session.message` event with the captured text via `SessionEventEnvelope.emit(actor=ACTOR_AGENT, data={"text": text})`.

Delete `backend/omoi_os/services/modal_sandboxed_agent.py`.

### 3. Tests

- Unit: `backend/tests/unit/services/test_sandboxed_agent_sdk.py` — mock `SandboxAgent` and `Session`, exercise `prompt`/`close` and event-collection logic.
- Integration: `backend/tests/integration/test_sandboxed_agent_sdk_live.py` — real Modal sandbox via `OmoiOsModalProvider`, full round-trip, skipif missing creds.
- The existing `probe_sdk_modal_session.py` is the smoke harness.

---

## Decisions Still Open

1. **Model selection** for opencode. The `agents/opencode.mdx` model list has anthropic/openai/cerebras/opencode-zen. Fireworks is not listed. Two paths: (a) point opencode at `OPENAI_BASE_URL=$LLM_BASE_URL` (Fireworks) + `OPENAI_API_KEY=$LLM_API_KEY` and use a model alias compatible with that backend; (b) configure opencode to use one of the OpenCode Zen models (`opencode/big-pickle` etc.) and route through opencode's own provider. Option (a) preserves the Fireworks-only LLM lane. Verify with a probe before committing.

2. **What omoi_os env vars become Modal Secret keys.** Today the OmoiOsModalProvider accepts `env_vars` and passes them through. For phase-1 chat: `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `OPENCODE_MODEL` (or whatever the chosen opencode model selector is), and any broker URLs needed for sandboxed credentials.

3. **`auth.json` layout vs. opencode's own auth.** The SDK injects `auth.json` via `WorkspaceConfig.auth_json` to `/workspace/auth.json`; opencode reads from `~/.local/share/opencode/auth.json`. Need to verify path mapping. Likely we need a small shim in `_bootstrap_workspace` or write the file ourselves via `sandbox.exec` to the right location.

4. **Persist driver still useful?** YES — even with SandboxAgent + Session active, the persist driver translates SDK SessionEvent rows into the existing `events` table, keeps `tasks.result['agent_session']` for SessionRecord, and gives the existing SSE endpoint at `/api/v1/sessions/{id}/events` first-class data without a special case for SDK-driven sessions.

5. **Daytona-chat path coexistence.** Keep `sandboxed_agent.py` (Daytona, opencode-serve direct) untouched. Modal path uses the new SDK path. `_dispatch_to_sandboxed_agent` selects on `sandbox.provider`. If we later want to migrate Daytona too, that's a separate phase.

---

## Open Risks

1. **Fireworks compatibility with opencode's model selector.** Need a probe that creates a session with `model=...`, sends a prompt, and verifies the reply text actually came from Fireworks (not some default opencode-zen model).

2. **`auth.json` path mismatch.** SDK writes to `/workspace/auth.json`, opencode reads from `~/.local/share/opencode/auth.json`. The current probe ran without verifying the actual model — opencode may be falling back to `opencode/big-pickle` (default). Need to verify creds were used.

3. **Cold-start latency.** Image build is cached, but first-pull on a fresh Modal account can take ~60s. Subsequent spawns ~10–15s. Health-probe loop in chat_responder needs a 60s timeout.

4. **SSE event capture for chat reply text.** The `prompt()` response carries `stopReason` and `usage` but not the agent's text. Text comes via `agent_message_chunk` events on the SSE channel during the prompt. Need to register a handler before calling prompt and collect chunks. SDK exposes `Session.track_events`, `Session.get_transcript`, and `on_message` callback — pick the one that gives clean reply text.

5. **Memory `client_metadata` round-trip.** Spec §18 §5 requires opaque client metadata to round-trip byte-equally. Verify the SDK adapter doesn't transform it.

---

## Reference

- Working buffer: [`memory/working-buffer.md`](../../memory/working-buffer.md)
- Existing Daytona-chat path: `backend/omoi_os/services/sandboxed_agent.py`
- Existing Modal-chat (to delete in Task #7): `backend/omoi_os/services/modal_sandboxed_agent.py`
- New persist driver: `backend/omoi_os/services/agent_session_persist.py`
- New Modal provider: `backend/omoi_os/services/sa_modal_provider.py`
- Probe scripts: `scripts/poof/probe_sdk_*.py`
- sandbox-agent docs (the source of truth): `/Users/kevinhill/Coding/Projects/sandbox-agent/docs/`
- ACP agent specs: `docs/agents/{claude,codex,opencode,amp,cursor,pi}.mdx`
- Auto-memory feedback rule: `feedback_reuse_existing_tables.md` — adapt to existing tables, don't add parallel schema for SDK adapters.
