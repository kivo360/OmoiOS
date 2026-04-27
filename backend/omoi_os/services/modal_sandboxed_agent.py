"""Modal-backed sandboxed agent — peer of `services.sandboxed_agent`.

Each OmoiOS session gets a dedicated Modal sandbox running a long-lived
``opencode serve`` process. We talk to it over Modal's encrypted-port
tunnel (port 4096) using the same HTTP shape as the Daytona path:

    POST   /session                          → create opencode session
    POST   /session/{id}/message             → send a turn (returns final body)
    GET    /event                            → SSE stream of every part-delta

This module's `prompt()` accepts an optional `on_part(event_type, payload)`
callback. When supplied, every opencode event scoped to our session is
awaited through it — `chat_responder` plumbs that into
`SessionEventEnvelope.emit("session.message.part.{type}", …)` so live SSE
clients see token-level streaming. With no callback, behavior is
backwards-compatible: returns the assembled assistant text as a string.

Public surface mirrors `services.sandboxed_agent`:

    agent = await get_or_spawn(omoios_session_id)
    reply = await agent.prompt("hello")
    reply = await agent.prompt("hello", on_part=cb)
    await close(omoios_session_id)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

import httpx
from httpx_sse import aconnect_sse

from omoi_os.logging import get_logger


logger = get_logger(__name__)


_DEFAULT_OPENCODE_MODEL = os.environ.get(
    "OPENCODE_MODAL_MODEL",
    "accounts/fireworks/routers/kimi-k2p5-turbo",
)
_DEFAULT_OPENCODE_PROVIDER = os.environ.get("OPENCODE_MODAL_PROVIDER", "fireworks-ai")
_OPENCODE_PORT = int(os.environ.get("OPENCODE_MODAL_PORT", "4096"))
_OPENCODE_BIN = "/root/.opencode/bin/opencode"
_OPENCODE_TURN_TIMEOUT_SECONDS = int(
    os.environ.get("OPENCODE_MODAL_TURN_TIMEOUT", "600")
)
_OPENCODE_HEALTH_TIMEOUT_SECONDS = int(
    os.environ.get("OPENCODE_MODAL_HEALTH_TIMEOUT", "90")
)


# Callback signature: (event_type, payload) where payload is a dict from
# opencode's `properties` field. Async so callers can await DB writes /
# Redis publishes inside the callback without spawning extra tasks.
PartCallback = Callable[[str, dict], Awaitable[None]]


@dataclass
class ModalSandboxedAgent:
    """One OmoiOS session ⇆ one Modal sandbox ⇆ one opencode serve process."""

    omoios_session_id: str
    sandbox_id: str
    spawner: Any  # ModalSpawnerService — Any keeps the import surface small
    tunnel_url: str
    opencode_session_id: str
    provider: str
    model: str
    spawned_at: float
    modal_object_id: Optional[str] = None
    runtime: str = "opencode-modal"
    _http: Optional[httpx.AsyncClient] = field(default=None, repr=False)

    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self.tunnel_url, timeout=_OPENCODE_TURN_TIMEOUT_SECONDS
            )
        return self._http

    async def prompt(
        self,
        text: str,
        *,
        on_part: Optional[PartCallback] = None,
    ) -> str:
        """Run one chat turn. Returns the assembled assistant text.

        If ``on_part`` is supplied, it's awaited for each opencode event
        scoped to this session — `message.part.delta`, `message.part.updated`,
        `message.updated`, `session.idle`, etc. The callback's first arg is
        the event type, the second is the event's `properties` dict (so
        consumers don't have to redundantly extract it).
        """
        client = self._client()
        sid = self.opencode_session_id
        parts_by_id: dict[str, dict] = {}
        # Queue events from the SSE reader to the chat-runner so the runner
        # can fan them out without blocking the SSE socket itself.
        queue: asyncio.Queue[Optional[tuple[str, dict]]] = asyncio.Queue()

        async def _read_events() -> None:
            try:
                async with aconnect_sse(client, "GET", "/event") as ev_source:
                    async for sse_evt in ev_source.aiter_sse():
                        try:
                            evt = json.loads(sse_evt.data)
                        except (json.JSONDecodeError, TypeError):
                            continue
                        if not _event_matches_session(evt, sid):
                            continue
                        et = evt.get("type")
                        props = evt.get("properties") or {}
                        if not isinstance(et, str):
                            continue
                        # Snapshot accumulator — used to assemble the final
                        # text if the chat POST body doesn't carry parts.
                        if et == "message.part.updated":
                            part = props.get("part")
                            if isinstance(part, dict) and isinstance(
                                part.get("id"), str
                            ):
                                parts_by_id[part["id"]] = part
                        await queue.put((et, props))
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "modal sandboxed agent: event reader failed",
                    omoios_session_id=self.omoios_session_id,
                    error=str(exc),
                )

        async def _send_turn() -> dict:
            r = await client.post(
                f"/session/{sid}/message",
                json={
                    "providerID": self.provider,
                    "modelID": self.model,
                    "parts": [{"type": "text", "text": text}],
                },
                timeout=_OPENCODE_TURN_TIMEOUT_SECONDS,
            )
            r.raise_for_status()
            return r.json()

        reader_task = asyncio.create_task(_read_events())
        # Tiny grace so the SSE handshake is up before the message POST —
        # opencode emits the first delta within a few hundred ms of the POST
        # completing, and we don't want to drop the leading reasoning bursts.
        await asyncio.sleep(0.05)
        chat_task = asyncio.create_task(_send_turn())

        try:
            while True:
                getter = asyncio.create_task(queue.get())
                done, _pending = await asyncio.wait(
                    {getter, chat_task}, return_when=asyncio.FIRST_COMPLETED
                )
                if getter in done:
                    item = getter.result()
                    if item is None:
                        if chat_task.done():
                            break
                        continue
                    et, props = item
                    if on_part is not None:
                        try:
                            await on_part(et, props)
                        except Exception as exc:  # noqa: BLE001
                            logger.warning(
                                "modal sandboxed agent: on_part raised",
                                omoios_session_id=self.omoios_session_id,
                                event_type=et,
                                error=str(exc),
                            )
                    if chat_task.done():
                        # Drain whatever's already in the queue, then exit.
                        while not queue.empty():
                            extra = queue.get_nowait()
                            if extra is None:
                                break
                            et2, props2 = extra
                            if on_part is not None:
                                with contextlib.suppress(Exception):
                                    await on_part(et2, props2)
                        break
                else:
                    getter.cancel()
                    with contextlib.suppress(asyncio.CancelledError, Exception):
                        await getter
                    # Give the reader a beat to flush any final
                    # `session.idle` / `message.updated` for the turn.
                    await asyncio.sleep(0.2)
                    while not queue.empty():
                        extra = queue.get_nowait()
                        if extra is None:
                            break
                        et2, props2 = extra
                        if on_part is not None:
                            with contextlib.suppress(Exception):
                                await on_part(et2, props2)
                    break

            try:
                final = await chat_task
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "modal sandboxed agent: chat POST failed",
                    omoios_session_id=self.omoios_session_id,
                    error=str(exc),
                )
                return ""
        finally:
            reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await reader_task

        # Authoritative parts come from the response body when the server
        # returns them; fall back to the SSE-streamed accumulator if not.
        assistant_message_id = (
            (final.get("info") or {}).get("id") if isinstance(final, dict) else None
        )
        final_parts = (final.get("parts") if isinstance(final, dict) else None) or [
            p
            for p in parts_by_id.values()
            if p.get("messageID") == assistant_message_id
        ]
        return _assemble_text(final_parts)

    async def close(self) -> None:
        if self._http is not None:
            with contextlib.suppress(Exception):
                await self._http.aclose()
            self._http = None
        try:
            await self.spawner.terminate_sandbox(self.sandbox_id)
        except Exception as exc:  # noqa: BLE001 — terminate is best-effort
            logger.warning(
                "modal sandboxed agent: terminate failed",
                omoios_session_id=self.omoios_session_id,
                sandbox_id=self.sandbox_id,
                error=str(exc),
            )

    def as_runtime_state(self) -> dict[str, Any]:
        return {
            "runtime": self.runtime,
            "status": "live",
            "sandbox_id": self.sandbox_id,
            "modal_object_id": self.modal_object_id,
            "tunnel_url": self.tunnel_url,
            "opencode_session_id": self.opencode_session_id,
            "provider": self.provider,
            "model": self.model,
            "spawned_at": self.spawned_at,
        }


# ─── registry ────────────────────────────────────────────────────────────────


_registry: dict[str, ModalSandboxedAgent] = {}
_spawn_lock = asyncio.Lock()


async def get_or_spawn(omoios_session_id: str) -> ModalSandboxedAgent:
    """Return a Modal sandboxed agent for this session.

    Lookup order:
      1. in-process cache (fast path)
      2. ``task.result.sandbox_agent`` → reattach via Modal ``Sandbox.from_id``,
         healthcheck the tunnel, verify the opencode session still exists
      3. fresh spawn → persist runtime state, return
    """
    existing = _registry.get(omoios_session_id)
    if existing is not None:
        return existing

    async with _spawn_lock:
        existing = _registry.get(omoios_session_id)
        if existing is not None:
            return existing

        rehydrated = await _rehydrate_agent(omoios_session_id)
        if rehydrated is not None:
            _registry[omoios_session_id] = rehydrated
            return rehydrated

        agent = await _spawn_agent(omoios_session_id)
        _registry[omoios_session_id] = agent
        await _persist_runtime_state(omoios_session_id, agent.as_runtime_state())
        return agent


async def close(omoios_session_id: str) -> None:
    agent = _registry.pop(omoios_session_id, None)
    if agent is not None:
        await agent.close()
        await _persist_runtime_state(
            omoios_session_id,
            {**agent.as_runtime_state(), "status": "closed"},
        )
        return
    # Cache miss: still tear down any persisted sandbox so a foreign-replica
    # spawn isn't left dangling.
    state = await _load_runtime_state(omoios_session_id)
    if not state or state.get("runtime") != "opencode-modal":
        return
    modal_object_id = state.get("modal_object_id")
    sandbox_id = state.get("sandbox_id")
    if not (modal_object_id and sandbox_id):
        return
    try:
        from omoi_os.services.modal_spawner import get_modal_spawner

        spawner = get_modal_spawner()
        attached = await spawner.register_foreign_sandbox(
            sandbox_id,
            modal_object_id,
            task_id=omoios_session_id,
        )
        if attached:
            await spawner.terminate_sandbox(sandbox_id)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "modal sandboxed agent: foreign teardown failed",
            omoios_session_id=omoios_session_id,
            sandbox_id=sandbox_id,
            error=str(exc),
        )
    await _persist_runtime_state(omoios_session_id, {**state, "status": "closed"})


async def close_all() -> None:
    for sid in list(_registry.keys()):
        try:
            await close(sid)
        except Exception:  # noqa: BLE001
            pass


def is_enabled() -> bool:
    """Return True iff the sandboxed-agent feature flag is on AND the
    configured sandbox provider is Modal."""
    try:
        from omoi_os.config import get_app_settings

        settings = get_app_settings()
        if not bool(settings.feature_flags.sandboxed_agent_enabled):
            return False
        return settings.sandbox.provider == "modal"
    except Exception:  # noqa: BLE001
        return False


# ─── spawn pipeline ──────────────────────────────────────────────────────────


async def _spawn_agent(omoios_session_id: str) -> ModalSandboxedAgent:
    from omoi_os.services.modal_spawner import get_modal_spawner

    spawner = get_modal_spawner()
    api_key = _resolve_llm_api_key()
    if not api_key:
        raise RuntimeError(
            "modal sandboxed agent requires LLM_API_KEY (or "
            "FIREWORKS_API_KEY) to render opencode auth.json"
        )

    logger.info(
        "modal sandboxed agent: spawning fresh sandbox",
        omoios_session_id=omoios_session_id,
    )
    sandbox_id = await spawner.spawn_for_task(
        task_id=omoios_session_id,
        agent_id=f"chat-{omoios_session_id[:8]}",
        phase_id="chat",
        execution_mode="chat",
        runtime="opencode",
        exposed_ports=[_OPENCODE_PORT],
    )

    await _write_opencode_configs(spawner, sandbox_id, api_key=api_key)
    await _start_opencode_serve(spawner, sandbox_id)

    info = spawner.get_sandbox_info(sandbox_id)
    modal_object_id = (
        info.extra_data.get("modal_object_id") if info is not None else None
    )
    tunnel_urls = (
        info.extra_data.get("tunnel_urls") if info is not None else None
    ) or {}
    tunnel_url = tunnel_urls.get(str(_OPENCODE_PORT))
    if not tunnel_url:
        raise RuntimeError(
            f"modal sandboxed agent: spawner did not surface tunnel for port "
            f"{_OPENCODE_PORT}; check exposed_ports propagation"
        )

    await _wait_for_opencode_health(tunnel_url)
    opencode_session_id = await _create_opencode_session(tunnel_url)

    return ModalSandboxedAgent(
        omoios_session_id=omoios_session_id,
        sandbox_id=sandbox_id,
        spawner=spawner,
        tunnel_url=tunnel_url,
        opencode_session_id=opencode_session_id,
        provider=_DEFAULT_OPENCODE_PROVIDER,
        model=_DEFAULT_OPENCODE_MODEL,
        spawned_at=time.time(),
        modal_object_id=modal_object_id,
    )


async def _start_opencode_serve(spawner: Any, sandbox_id: str) -> None:
    """Boot ``opencode serve`` as a backgrounded process inside the sandbox."""
    cmd = (
        f"nohup {_OPENCODE_BIN} serve --port {_OPENCODE_PORT} --hostname 0.0.0.0 "
        "> /tmp/opencode-serve.log 2>&1 &"
    )
    await spawner.exec(sandbox_id, "bash", "-lc", cmd)


async def _wait_for_opencode_health(
    tunnel_url: str, *, timeout_s: float = float(_OPENCODE_HEALTH_TIMEOUT_SECONDS)
) -> None:
    deadline = time.monotonic() + timeout_s
    last: Optional[str] = None
    async with httpx.AsyncClient(timeout=3.0) as c:
        while time.monotonic() < deadline:
            try:
                r = await c.get(f"{tunnel_url}/global/health")
                if r.status_code == 200:
                    return
                last = f"http {r.status_code}"
            except Exception as exc:  # noqa: BLE001
                last = type(exc).__name__
            await asyncio.sleep(1.5)
    raise RuntimeError(
        f"modal sandboxed agent: opencode never became healthy at "
        f"{tunnel_url} (last: {last})"
    )


async def _create_opencode_session(tunnel_url: str) -> str:
    """Mint one opencode session for the lifetime of this Modal sandbox.

    opencode 1.14.x rejects empty bodies on ``POST /session`` — the server
    reads JSON before checking content; a missing body 400s with
    ``Malformed JSON in request body``. Send ``{}``.
    """
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(f"{tunnel_url}/session", json={})
        r.raise_for_status()
        return r.json()["id"]


async def _write_opencode_configs(
    spawner: Any, sandbox_id: str, *, api_key: str
) -> None:
    """Render opencode.json, oh-my-openagent.jsonc, and auth.json into the sandbox.

    Reuses the project's canonical renderers (``opencode_config_renderer``)
    so chat-mode SDK-direct sessions produce identical config bodies to
    env_version-driven spawns. Aliases match opencode's catalog ids — for
    the chat lane that's just ``fireworks-ai``.
    """
    from omoi_os.services.opencode_config_renderer import (
        render_auth_json,
        render_omo_config,
        render_opencode_config,
    )

    aliases = [_DEFAULT_OPENCODE_PROVIDER]
    opencode_body = render_opencode_config(
        aliases, default_model=f"{_DEFAULT_OPENCODE_PROVIDER}/{_DEFAULT_OPENCODE_MODEL}"
    ).encode("utf-8")
    omo_body = render_omo_config(
        aliases, default_model=f"{_DEFAULT_OPENCODE_PROVIDER}/{_DEFAULT_OPENCODE_MODEL}"
    ).encode("utf-8")
    auth_body = render_auth_json(
        {_DEFAULT_OPENCODE_PROVIDER: {"kind": "bearer_secret", "value": api_key}}
    ).encode("utf-8")

    await spawner.exec(sandbox_id, "mkdir", "-p", "/root/.config/opencode")
    await spawner.exec(sandbox_id, "mkdir", "-p", "/root/.local/share/opencode")
    await spawner.upload_file(
        sandbox_id, "/root/.config/opencode/opencode.json", opencode_body
    )
    await spawner.upload_file(
        sandbox_id, "/root/.config/opencode/oh-my-openagent.jsonc", omo_body
    )
    await spawner.upload_file(
        sandbox_id, "/root/.local/share/opencode/auth.json", auth_body
    )


def _resolve_llm_api_key() -> Optional[str]:
    return os.environ.get("FIREWORKS_API_KEY") or os.environ.get("LLM_API_KEY")


# ─── persistence + cross-replica rehydration ─────────────────────────────────


# Mirrors ``services.sandboxed_agent._MAX_AGENT_AGE_SECONDS``. Modal's default
# sandbox timeout is 24h via ``sandbox_timeout_seconds`` on the spawner; we
# treat anything older than 6h as "probably reaped" and fall through to a
# fresh spawn rather than burn a round-trip on a doomed reattach.
_MAX_AGENT_AGE_SECONDS = 60 * 60 * 6


async def _persist_runtime_state(omoios_session_id: str, state: dict[str, Any]) -> None:
    """Merge ``state`` into ``task.result.sandbox_agent`` for this session.

    Best-effort — persistence failures must never block a chat turn.
    """
    try:
        from omoi_os.api.dependencies import get_db_service
        from omoi_os.models.task import Task
        from sqlalchemy.orm.attributes import flag_modified

        db = get_db_service()
        with db.get_session() as session:
            task = session.get(Task, omoios_session_id)
            if task is None:
                return
            result = dict(task.result or {})
            result["sandbox_agent"] = {
                **(result.get("sandbox_agent") or {}),
                **state,
            }
            task.result = result
            flag_modified(task, "result")
            session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "modal sandboxed agent: persist runtime state failed",
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
            return state if isinstance(state, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "modal sandboxed agent: load runtime state failed",
            omoios_session_id=omoios_session_id,
            error=str(exc),
        )
        return None


async def _rehydrate_agent(
    omoios_session_id: str,
) -> Optional[ModalSandboxedAgent]:
    """Try to reattach to a Modal sandbox spawned by another replica.

    Reads ``task.result['sandbox_agent']``. If it's a Modal entry, still
    "live", and not too stale, re-attaches via ``register_foreign_sandbox``,
    then verifies the persisted ``tunnel_url`` is still healthy and the
    persisted ``opencode_session_id`` is still listed by the server. Returns
    None on any failure — the caller falls through to a fresh spawn.
    """
    state = await _load_runtime_state(omoios_session_id)
    if not state:
        return None
    if state.get("runtime") != "opencode-modal":
        return None
    if state.get("status") in ("closed", "error"):
        return None

    sandbox_id = state.get("sandbox_id")
    modal_object_id = state.get("modal_object_id")
    tunnel_url = state.get("tunnel_url")
    persisted_session_id = state.get("opencode_session_id")
    if not (sandbox_id and modal_object_id and tunnel_url and persisted_session_id):
        # Old (exec-mode) state row — force fresh spawn so we get a tunnel.
        return None

    spawned_at = float(state.get("spawned_at") or 0)
    if spawned_at and time.time() - spawned_at > _MAX_AGENT_AGE_SECONDS:
        logger.info(
            "modal sandboxed agent: persisted state too old, skipping rehydration",
            omoios_session_id=omoios_session_id,
            age_s=time.time() - spawned_at,
        )
        return None

    from omoi_os.services.modal_spawner import get_modal_spawner

    spawner = get_modal_spawner()
    attached = await spawner.register_foreign_sandbox(
        sandbox_id,
        modal_object_id,
        task_id=omoios_session_id,
    )
    if not attached:
        await _persist_runtime_state(omoios_session_id, {**state, "status": "error"})
        return None

    # Tunnel + session-existence probe — covers the case where the sandbox
    # is alive but opencode-serve crashed / the session was reaped.
    if not await _probe_tunnel_alive(tunnel_url):
        logger.info(
            "modal sandboxed agent: persisted tunnel unhealthy, skipping rehydration",
            omoios_session_id=omoios_session_id,
            tunnel_url=tunnel_url,
        )
        await _persist_runtime_state(omoios_session_id, {**state, "status": "error"})
        return None

    if not await _opencode_session_exists(tunnel_url, persisted_session_id):
        logger.info(
            "modal sandboxed agent: opencode session vanished — recreating",
            omoios_session_id=omoios_session_id,
        )
        try:
            persisted_session_id = await _create_opencode_session(tunnel_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "modal sandboxed agent: failed to recreate opencode session",
                omoios_session_id=omoios_session_id,
                error=str(exc),
            )
            await _persist_runtime_state(
                omoios_session_id, {**state, "status": "error"}
            )
            return None

    logger.info(
        "modal sandboxed agent: rehydrated from persisted state",
        omoios_session_id=omoios_session_id,
        sandbox_id=sandbox_id,
        modal_object_id=modal_object_id,
    )
    return ModalSandboxedAgent(
        omoios_session_id=omoios_session_id,
        sandbox_id=sandbox_id,
        spawner=spawner,
        tunnel_url=tunnel_url,
        opencode_session_id=persisted_session_id,
        provider=state.get("provider") or _DEFAULT_OPENCODE_PROVIDER,
        model=state.get("model") or _DEFAULT_OPENCODE_MODEL,
        spawned_at=spawned_at or time.time(),
        modal_object_id=modal_object_id,
    )


async def _probe_tunnel_alive(tunnel_url: str, *, timeout_s: float = 4.0) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as c:
            r = await c.get(f"{tunnel_url}/global/health")
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


async def _opencode_session_exists(
    tunnel_url: str, opencode_session_id: str, *, timeout_s: float = 4.0
) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as c:
            r = await c.get(f"{tunnel_url}/session")
        if r.status_code != 200:
            return False
        return any(s.get("id") == opencode_session_id for s in r.json())
    except Exception:  # noqa: BLE001
        return False


# ─── helpers ─────────────────────────────────────────────────────────────────


def _event_matches_session(evt: Any, opencode_session_id: str) -> bool:
    """Check whether an opencode event is scoped to our session.

    opencode emits a global ``/event`` feed; consumers filter by sessionID.
    Different event types put the sid in different places — we check all
    the spots.
    """
    if not isinstance(evt, dict):
        return False
    props = evt.get("properties") or {}
    if not isinstance(props, dict):
        return False
    if props.get("sessionID") == opencode_session_id:
        return True
    part = props.get("part") or {}
    if isinstance(part, dict) and part.get("sessionID") == opencode_session_id:
        return True
    info = props.get("info") or {}
    if isinstance(info, dict):
        if info.get("sessionID") == opencode_session_id:
            return True
        if info.get("id") == opencode_session_id:
            return True
    return False


def _assemble_text(parts: list) -> str:
    """Concatenate the text from any ``text``-type parts in order."""
    chunks: list[str] = []
    for p in parts or []:
        if not isinstance(p, dict):
            continue
        if p.get("type") != "text":
            continue
        t = p.get("text")
        if isinstance(t, str) and t:
            chunks.append(t)
    return "\n".join(chunks).strip()
