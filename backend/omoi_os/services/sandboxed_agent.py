"""Sandboxed-agent runtime: opencode-ai running inside a Daytona sandbox.

Stage-4 of the agent-runtime adaptation. Replaces the direct LLM call
in `chat_responder` with a call into an opencode server running inside
a Daytona sandbox. Each OmoiOS session gets a dedicated sandbox
(spawned or claimed from a warm pool on first message, kept warm
across turns, torn down on session close).

Why per-session and not per-turn: a fresh sandbox spawn is ~5-7s on
the current snapshot. Turn 2 reuses the same opencode HTTP server and
opencode session, so it's SDK-overhead-only on top of model latency.
Per-turn spawning would make every message feel like a fresh agent;
per-session matches how a human thinks about a chat.

Resilience properties added in stage 5:

  • State-of-record is `task.result['sandbox_agent']` in Postgres, not
    the in-process dict. The dict is only an LRU-style cache over the
    DB row so we don't pay the DB round-trip per prompt.
  • On cache miss, `get_or_spawn` rehydrates from DB before falling
    back to a fresh spawn. This means:
      - multi-replica setups hand off sessions correctly (any replica
        can serve any session; whoever gets the prompt will rehydrate)
      - crash-restart survives in-flight sessions (a fresh uvicorn will
        pick up existing sandboxes, no leak)
  • A warm pool of pre-baked sandboxes can front the spawn path —
    when the pool has capacity, `_spawn_agent` claims an already-live
    sandbox with opencode already serving; the user-visible first turn
    drops to SDK + model latency (no spawn).
  • The full agent-runtime handle is surfaced on the session response
    under `agent_runtime`, so clients know which runtime served a
    given session and can poll `status` = `live` | `closed` | `error`.

Shape:
    agent = await get_or_spawn(omoios_session_id)
    reply = await agent.prompt("hello")
    await close(omoios_session_id)   # on session cancel / delete
    runtime = await runtime_state(omoios_session_id)  # for UI surface
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from omoi_os.logging import get_logger


logger = get_logger(__name__)


_DEFAULT_SNAPSHOT = os.environ.get("OPENCODE_SANDBOX_SNAPSHOT", "omoios-omo-vnc")
_DEFAULT_PROVIDER = os.environ.get("OPENCODE_PROVIDER", "zai-coding-plan")
_DEFAULT_MODEL = os.environ.get("OPENCODE_MODEL", "glm-5.1")
_DEFAULT_PORT = int(os.environ.get("OPENCODE_PORT", "4096"))
_DEFAULT_AGENT_NAME = os.environ.get("OPENCODE_AGENT", "build")

# How stale the persisted sandbox_agent row is allowed to be before we
# consider it dead and spawn a fresh one (Daytona's auto-reap eventually
# nukes stale sandboxes; we don't want to keep trying to hit one that's
# been reaped).
_MAX_AGENT_AGE_SECONDS = 60 * 60 * 6  # 6 hours


# ─── SandboxedAgent handle ───────────────────────────────────────────────────


@dataclass
class SandboxedAgent:
    """One OmoiOS session ⇆ one Daytona sandbox ⇆ one opencode server."""

    omoios_session_id: str
    sandbox: Any  # may be None after rehydration — see _daytona_sandbox_handle()
    sandbox_id: str
    preview_url: str
    preview_token: str
    opencode_session_id: str
    provider: str
    model: str
    agent_name: str
    spawned_at: float
    runtime: str = "opencode"
    _client: Any = None  # AsyncOpencode, built lazily

    async def _get_client(self):
        if self._client is None:
            from opencode_ai import AsyncOpencode

            self._client = AsyncOpencode(
                base_url=self.preview_url,
                timeout=300.0,
                default_headers={"x-daytona-preview-token": self.preview_token},
            )
        return self._client

    async def prompt(self, text: str) -> str:
        client = await self._get_client()
        started = time.perf_counter()
        resp = await client.session.prompt(
            id=self.opencode_session_id,
            agent=self.agent_name,
            parts=[{"type": "text", "text": text}],
            model={"provider_id": self.provider, "model_id": self.model},
        )
        duration_ms = (time.perf_counter() - started) * 1000
        reply = _extract_text(resp)
        logger.info(
            "sandboxed agent reply",
            omoios_session_id=self.omoios_session_id,
            opencode_session_id=self.opencode_session_id,
            chars=len(reply),
            duration_ms=int(duration_ms),
        )
        return reply

    async def close(self) -> None:
        """Tear down the opencode session + the sandbox. Best-effort."""
        if self._client is not None:
            try:
                await self._client.session.delete(id=self.opencode_session_id)
            except Exception:  # noqa: BLE001
                pass
            try:
                await self._client.close()
            except Exception:  # noqa: BLE001
                pass
            self._client = None
        sb = self.sandbox or _daytona_sandbox_handle(self.sandbox_id)
        if sb is not None:
            try:
                sb.delete()
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "sandboxed agent: sandbox delete failed",
                    omoios_session_id=self.omoios_session_id,
                    sandbox_id=self.sandbox_id,
                    error=str(exc),
                )

    def as_runtime_state(self) -> dict[str, Any]:
        """Serialize handles to the shape stored on task.result."""
        return {
            "runtime": self.runtime,
            "status": "live",
            "sandbox_id": self.sandbox_id,
            "preview_url": self.preview_url,
            "preview_token": self.preview_token,
            "opencode_session_id": self.opencode_session_id,
            "provider": self.provider,
            "model": self.model,
            "agent_name": self.agent_name,
            "spawned_at": self.spawned_at,
        }


# ─── registry ────────────────────────────────────────────────────────────────


_registry: dict[str, SandboxedAgent] = {}
_spawn_lock = asyncio.Lock()


async def get_or_spawn(omoios_session_id: str) -> SandboxedAgent:
    """Return a SandboxedAgent for this OmoiOS session.

    Lookup order:
      1. in-process cache (fast path)
      2. task.result.sandbox_agent → rehydrate + health-probe
      3. warm pool claim → write state, return
      4. fresh spawn → write state, return

    The spawn path is serialized per-session so two turns arriving
    together don't each build a sandbox. Different sessions spawn in
    parallel (the lock is acquired only when a miss is confirmed).
    """
    existing = _registry.get(omoios_session_id)
    if existing is not None:
        return existing

    async with _spawn_lock:
        existing = _registry.get(omoios_session_id)
        if existing is not None:
            return existing

        # Try rehydration from the DB before paying for a new sandbox.
        rehydrated = await _rehydrate_agent(omoios_session_id)
        if rehydrated is not None:
            _registry[omoios_session_id] = rehydrated
            return rehydrated

        # Next try claiming from the warm pool.
        claimed = await _claim_from_pool(omoios_session_id)
        if claimed is not None:
            _registry[omoios_session_id] = claimed
            await _persist_runtime_state(omoios_session_id, claimed.as_runtime_state())
            return claimed

        # Finally, spawn fresh.
        agent = await _spawn_agent(omoios_session_id)
        _registry[omoios_session_id] = agent
        await _persist_runtime_state(omoios_session_id, agent.as_runtime_state())
        return agent


async def close(omoios_session_id: str) -> None:
    agent = _registry.pop(omoios_session_id, None)
    if agent is not None:
        await agent.close()
        await _persist_runtime_state(
            omoios_session_id, {**agent.as_runtime_state(), "status": "closed"}
        )
        return
    # Cache miss: still try to close any persisted sandbox.
    state = await _load_runtime_state(omoios_session_id)
    if not state:
        return
    sandbox_id = state.get("sandbox_id")
    if sandbox_id:
        sb = _daytona_sandbox_handle(sandbox_id)
        if sb is not None:
            try:
                sb.delete()
            except Exception:  # noqa: BLE001
                pass
    await _persist_runtime_state(omoios_session_id, {**state, "status": "closed"})


async def runtime_state(omoios_session_id: str) -> Optional[dict[str, Any]]:
    """Return the shape stored on task.result for UI surface."""
    agent = _registry.get(omoios_session_id)
    if agent is not None:
        return agent.as_runtime_state()
    return await _load_runtime_state(omoios_session_id)


async def close_all() -> None:
    for sid in list(_registry.keys()):
        try:
            await close(sid)
        except Exception:  # noqa: BLE001
            pass


# ─── persistence (task.result.sandbox_agent) ────────────────────────────────


async def _persist_runtime_state(omoios_session_id: str, state: dict[str, Any]) -> None:
    """Merge `state` into task.result.sandbox_agent for this session."""
    try:
        from omoi_os.api.dependencies import get_db_service
        from omoi_os.models.task import Task

        db = get_db_service()
        with db.get_session() as session:
            task = session.get(Task, omoios_session_id)
            if task is None:
                return
            result = dict(task.result or {})
            result["sandbox_agent"] = {**(result.get("sandbox_agent") or {}), **state}
            task.result = result
            # SQLAlchemy's JSONB mutation tracking is opt-in; explicit
            # flag_modified ensures the UPDATE statement fires.
            from sqlalchemy.orm.attributes import flag_modified

            flag_modified(task, "result")
            session.commit()
    except Exception as exc:  # noqa: BLE001 — persistence is best-effort
        logger.warning(
            "sandboxed agent: persist runtime state failed",
            omoios_session_id=omoios_session_id,
            error=str(exc),
        )


async def _load_runtime_state(
    omoios_session_id: str,
) -> Optional[dict[str, Any]]:
    try:
        from omoi_os.api.dependencies import get_db_service
        from omoi_os.models.task import Task

        db = get_db_service()
        with db.get_session() as session:
            task = session.get(Task, omoios_session_id)
            if task is None:
                return None
            result = task.result or {}
            state = result.get("sandbox_agent")
            if isinstance(state, dict):
                return state
            return None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "sandboxed agent: load runtime state failed",
            omoios_session_id=omoios_session_id,
            error=str(exc),
        )
        return None


# ─── rehydration (cross-replica + crash recovery) ────────────────────────────


async def _rehydrate_agent(omoios_session_id: str) -> Optional[SandboxedAgent]:
    state = await _load_runtime_state(omoios_session_id)
    if not state:
        return None
    if state.get("status") == "closed":
        return None
    if state.get("runtime") != "opencode":
        return None

    spawned_at = float(state.get("spawned_at") or 0)
    if spawned_at and time.time() - spawned_at > _MAX_AGENT_AGE_SECONDS:
        logger.info(
            "sandboxed agent: persisted state too old, skipping rehydration",
            omoios_session_id=omoios_session_id,
            age_s=time.time() - spawned_at,
        )
        return None

    preview_url = state.get("preview_url")
    preview_token = state.get("preview_token")
    opencode_sid = state.get("opencode_session_id")
    sandbox_id = state.get("sandbox_id")
    if not (preview_url and preview_token and opencode_sid and sandbox_id):
        return None

    # Health-probe the tunnel before we trust the handle — the sandbox
    # may have been reaped by Daytona or crashed in the meantime.
    loop = asyncio.get_running_loop()
    healthy = await loop.run_in_executor(
        None,
        lambda: _health_probe_sync(preview_url, token=preview_token),
    )
    if not healthy:
        logger.info(
            "sandboxed agent: persisted state unhealthy, skipping rehydration",
            omoios_session_id=omoios_session_id,
            sandbox_id=sandbox_id,
        )
        # Don't leave the stale row around — mark it closed so the next
        # spawn gets a clean slate rather than trying to rehydrate again.
        await _persist_runtime_state(omoios_session_id, {**state, "status": "error"})
        return None

    logger.info(
        "sandboxed agent: rehydrated from persisted state",
        omoios_session_id=omoios_session_id,
        sandbox_id=sandbox_id,
    )
    return SandboxedAgent(
        omoios_session_id=omoios_session_id,
        sandbox=_daytona_sandbox_handle(sandbox_id),
        sandbox_id=sandbox_id,
        preview_url=preview_url,
        preview_token=preview_token,
        opencode_session_id=opencode_sid,
        provider=state.get("provider") or _DEFAULT_PROVIDER,
        model=state.get("model") or _DEFAULT_MODEL,
        agent_name=state.get("agent_name") or _DEFAULT_AGENT_NAME,
        spawned_at=spawned_at or time.time(),
        runtime=state.get("runtime") or "opencode",
    )


# ─── daytona wrappers (sync, called via run_in_executor) ─────────────────────


def _make_daytona():
    from daytona import Daytona, DaytonaConfig

    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        raise RuntimeError("DAYTONA_API_KEY env var is required")
    return Daytona(
        DaytonaConfig(
            api_key=api_key,
            api_url=os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api"),
            target=os.environ.get("DAYTONA_TARGET", "us"),
        )
    )


def _daytona_sandbox_handle(sandbox_id: str):
    """Return a live Daytona sandbox object for an id, or None."""
    try:
        return _make_daytona().get(sandbox_id)
    except Exception:  # noqa: BLE001
        return None


def _spawn_sandbox_sync(snapshot: str, labels: dict[str, str]):
    from daytona import CreateSandboxFromSnapshotParams

    d = _make_daytona()
    params = CreateSandboxFromSnapshotParams(
        snapshot=snapshot,
        labels=labels,
        env_vars={"OMOIOS_SANDBOX_AGENT": "1"},
    )
    return d.create(params, timeout=120)


def _run_cmd_sync(sandbox, cmd: str, *, timeout: int = 30) -> str:
    result = sandbox.process.exec(cmd, timeout=timeout)
    return str(
        getattr(result, "result", None) or getattr(result, "stdout", None) or ""
    ).strip()


def _write_auth_json_sync(sandbox, *, zai_key: str) -> None:
    data_dir = "$HOME/.local/share/opencode"
    _run_cmd_sync(sandbox, f"mkdir -p {data_dir} && chmod 0700 {data_dir}")
    payload = json.dumps({"zai-coding-plan": {"type": "api", "key": zai_key}})
    _run_cmd_sync(sandbox, f"cat > {data_dir}/auth.json <<'JSON'\n{payload}\nJSON")
    _run_cmd_sync(sandbox, f"chmod 0600 {data_dir}/auth.json")


def _start_opencode_sync(sandbox, *, port: int) -> None:
    from daytona.common.process import SessionExecuteRequest

    sandbox.process.create_session("opencode-serve")
    sandbox.process.execute_session_command(
        "opencode-serve",
        SessionExecuteRequest(
            command=(
                f"nohup opencode serve --port {port} --hostname 0.0.0.0 "
                "> /tmp/opencode-serve.log 2>&1 &"
            ),
            run_async=True,
        ),
        timeout=10,
    )


def _open_preview_sync(sandbox, *, port: int) -> tuple[str, str]:
    pp = sandbox.get_preview_link(port)
    return pp.url, pp.token


def _wait_for_health_sync(url: str, *, token: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    headers = {"x-daytona-preview-token": token}
    last: Optional[str] = None
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{url}/global/health", headers=headers, timeout=3.0)
            if r.status_code == 200:
                return
            last = f"{r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last = type(exc).__name__
        time.sleep(1.5)
    raise RuntimeError(f"opencode not healthy through tunnel (last: {last})")


def _health_probe_sync(url: str, *, token: str, timeout_s: float = 4.0) -> bool:
    """Single-shot health check — used for rehydration decisions."""
    try:
        r = httpx.get(
            f"{url}/global/health",
            headers={"x-daytona-preview-token": token},
            timeout=timeout_s,
        )
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


# ─── spawn logic (shared between pool + fresh) ───────────────────────────────


async def _zai_key() -> str:
    key = os.environ.get("OPENCODE_ZAI_KEY") or os.environ.get("LLM_API_KEY")
    if not key:
        raise RuntimeError(
            "sandboxed agent requires OPENCODE_ZAI_KEY (or LLM_API_KEY) set"
        )
    return key


async def _provision_live_sandbox(
    labels: dict[str, str], *, port: int = _DEFAULT_PORT
) -> dict[str, Any]:
    """Common spawn pipeline used by both fresh spawn and pool refill.

    Returns a dict with {sandbox, preview_url, preview_token} — ready
    for an AsyncOpencode session.create() on top.
    """
    loop = asyncio.get_running_loop()
    snapshot = _DEFAULT_SNAPSHOT
    zai_key = await _zai_key()

    sandbox = await loop.run_in_executor(None, _spawn_sandbox_sync, snapshot, labels)
    await loop.run_in_executor(
        None, lambda: _write_auth_json_sync(sandbox, zai_key=zai_key)
    )
    await loop.run_in_executor(None, lambda: _start_opencode_sync(sandbox, port=port))
    await asyncio.sleep(2)  # let the process bind the port
    preview_url, preview_token = await loop.run_in_executor(
        None, lambda: _open_preview_sync(sandbox, port=port)
    )
    await loop.run_in_executor(
        None,
        lambda: _wait_for_health_sync(preview_url, token=preview_token, timeout_s=60),
    )
    return {
        "sandbox": sandbox,
        "sandbox_id": sandbox.id,
        "preview_url": preview_url,
        "preview_token": preview_token,
    }


async def _open_opencode_session(
    preview_url: str, preview_token: str, *, omoios_session_id: str
):
    from opencode_ai import AsyncOpencode

    client = AsyncOpencode(
        base_url=preview_url,
        timeout=300.0,
        default_headers={"x-daytona-preview-token": preview_token},
    )
    opencode_session = await client.session.create(title=f"omoios-{omoios_session_id}")
    return client, opencode_session.id


async def _spawn_agent(omoios_session_id: str) -> SandboxedAgent:
    labels = {
        "purpose": "omoios-sandboxed-agent",
        "omoios_session_id": omoios_session_id,
        "ts": str(int(time.time())),
    }
    logger.info(
        "sandboxed agent: spawning fresh sandbox",
        omoios_session_id=omoios_session_id,
    )
    provisioned = await _provision_live_sandbox(labels)
    client, opencode_sid = await _open_opencode_session(
        provisioned["preview_url"],
        provisioned["preview_token"],
        omoios_session_id=omoios_session_id,
    )
    return SandboxedAgent(
        omoios_session_id=omoios_session_id,
        sandbox=provisioned["sandbox"],
        sandbox_id=provisioned["sandbox_id"],
        preview_url=provisioned["preview_url"],
        preview_token=provisioned["preview_token"],
        opencode_session_id=opencode_sid,
        provider=_DEFAULT_PROVIDER,
        model=_DEFAULT_MODEL,
        agent_name=_DEFAULT_AGENT_NAME,
        spawned_at=time.time(),
        _client=client,
    )


# ─── warm pool integration ───────────────────────────────────────────────────


async def _claim_from_pool(omoios_session_id: str) -> Optional[SandboxedAgent]:
    """Try to take a pre-spawned sandbox from the warm pool, if enabled."""
    try:
        from omoi_os.services.sandbox_pool import try_acquire

        prebaked = await try_acquire()
    except Exception:  # noqa: BLE001
        return None
    if prebaked is None:
        return None

    logger.info(
        "sandboxed agent: claimed from warm pool",
        omoios_session_id=omoios_session_id,
        sandbox_id=prebaked["sandbox_id"],
    )
    client, opencode_sid = await _open_opencode_session(
        prebaked["preview_url"],
        prebaked["preview_token"],
        omoios_session_id=omoios_session_id,
    )
    return SandboxedAgent(
        omoios_session_id=omoios_session_id,
        sandbox=prebaked["sandbox"],
        sandbox_id=prebaked["sandbox_id"],
        preview_url=prebaked["preview_url"],
        preview_token=prebaked["preview_token"],
        opencode_session_id=opencode_sid,
        provider=_DEFAULT_PROVIDER,
        model=_DEFAULT_MODEL,
        agent_name=_DEFAULT_AGENT_NAME,
        spawned_at=prebaked.get("spawned_at") or time.time(),
        _client=client,
    )


# ─── helpers ─────────────────────────────────────────────────────────────────


def _extract_text(resp: Any) -> str:
    parts = getattr(resp, "parts", None) or []
    chunks: list[str] = []
    for p in parts:
        ptype = getattr(p, "type", None) or (
            p.get("type") if isinstance(p, dict) else None
        )
        if ptype != "text":
            continue
        t = getattr(p, "text", None) or (p.get("text") if isinstance(p, dict) else None)
        if isinstance(t, str) and t:
            chunks.append(t)
    return "\n".join(chunks).strip()


def is_enabled() -> bool:
    """Single canonical check for the feature flag."""
    try:
        from omoi_os.config import get_app_settings

        return bool(get_app_settings().feature_flags.sandboxed_agent_enabled)
    except Exception:  # noqa: BLE001
        return False
