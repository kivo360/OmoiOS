"""Modal-backed sandboxed agent — peer of `services.sandboxed_agent`.

The Daytona path runs `opencode serve` (a long-lived HTTP server) inside the
sandbox and routes prompts via the AsyncOpencode client through a preview
tunnel. Modal sandboxes don't ship the same preview-URL primitive (Modal's
`tunnels()` requires `encrypted_ports` declared at create time and is meant
for HTTP services, not low-latency RPC), so this module instead drives
opencode in single-shot mode via `sandbox.exec`:

    bash -lc 'cd /tmp && timeout 60 /root/.opencode/bin/opencode run \\
        --print-logs --log-level ERROR --dangerously-skip-permissions \\
        <prompt> < /dev/null'

The pattern is the one we proved in `scripts/modal_sandbox_smoke.py` (mode=
llm) — opencode is baked into the image at build time, stdin is closed with
`< /dev/null` so opencode doesn't hang waiting for input, and a hard
`timeout 60` guards against runaway calls.

Each OmoiOS session gets a dedicated Modal sandbox; the sandbox is kept
alive across turns (sleep infinity) and torn down on session close.
Continuity across turns is *not* preserved at the opencode-session layer —
each turn is a fresh `opencode run`. The chat_responder bakes the prior
conversation into the prompt itself, so the LLM sees the history regardless.

Public surface mirrors `services.sandboxed_agent` so chat_responder can
dispatch through either runtime via a single protocol:

    agent = await get_or_spawn(omoios_session_id)
    reply = await agent.prompt("hello")
    await close(omoios_session_id)
"""

from __future__ import annotations

import asyncio
import json
import os
import shlex
import time
from dataclasses import dataclass
from typing import Any, Optional

from omoi_os.logging import get_logger


logger = get_logger(__name__)


_DEFAULT_OPENCODE_MODEL = os.environ.get(
    "OPENCODE_MODAL_MODEL",
    "fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo",
)
_OPENCODE_BIN = "/root/.opencode/bin/opencode"
_OPENCODE_RUN_TIMEOUT_SECONDS = int(os.environ.get("OPENCODE_MODAL_RUN_TIMEOUT", "60"))


@dataclass
class ModalSandboxedAgent:
    """One OmoiOS session ⇆ one Modal sandbox ⇆ single-shot opencode runs."""

    omoios_session_id: str
    sandbox_id: str
    spawner: Any  # ModalSpawnerService — typed as Any to keep import cheap
    provider: str
    model: str
    spawned_at: float
    runtime: str = "opencode-modal"

    async def prompt(self, text: str) -> str:
        """Run one opencode turn against the user's text. Returns the reply."""
        # Quote the prompt for `bash -lc` so shell metacharacters don't
        # detonate the command. shlex handles single-quoting + escaping
        # the way bash expects.
        quoted_prompt = shlex.quote(text)
        cmd = (
            f"cd /tmp && timeout {_OPENCODE_RUN_TIMEOUT_SECONDS} {_OPENCODE_BIN} run "
            "--print-logs --log-level ERROR --dangerously-skip-permissions "
            f"{quoted_prompt} < /dev/null"
        )
        started = time.perf_counter()
        result = await self.spawner.exec(self.sandbox_id, "bash", "-lc", cmd)
        duration_ms = (time.perf_counter() - started) * 1000

        stdout = _to_text(result.get("stdout"))
        stderr = _to_text(result.get("stderr"))
        rc = result.get("exit_code", -1)

        if rc != 0:
            logger.warning(
                "modal sandboxed agent: opencode run failed",
                omoios_session_id=self.omoios_session_id,
                sandbox_id=self.sandbox_id,
                exit_code=rc,
                stderr_preview=stderr[:200],
                duration_ms=int(duration_ms),
            )
            # Surface a non-empty string so the caller can decide whether
            # to fall back to direct LLM. An empty reply is interpreted
            # by chat_responder as "no agent message" and triggers fallback.
            return ""

        reply = _extract_opencode_reply(stdout)
        logger.info(
            "modal sandboxed agent: reply",
            omoios_session_id=self.omoios_session_id,
            sandbox_id=self.sandbox_id,
            chars=len(reply),
            duration_ms=int(duration_ms),
        )
        return reply

    async def close(self) -> None:
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
            "provider": self.provider,
            "model": self.model,
            "spawned_at": self.spawned_at,
        }


# ─── registry ────────────────────────────────────────────────────────────────


_registry: dict[str, ModalSandboxedAgent] = {}
_spawn_lock = asyncio.Lock()


async def get_or_spawn(omoios_session_id: str) -> ModalSandboxedAgent:
    """Return a Modal sandboxed agent for this session.

    In-memory cache only — multi-replica rehydration via task.result is
    deferred until we have a durable Modal sandbox handle (Modal's
    `Sandbox.from_id` exists but the spawner doesn't currently re-register
    foreign sandboxes in `_sandboxes`, so a fresh process can't drive a
    pre-existing sandbox). For single-replica dev this is sufficient.
    """
    existing = _registry.get(omoios_session_id)
    if existing is not None:
        return existing

    async with _spawn_lock:
        existing = _registry.get(omoios_session_id)
        if existing is not None:
            return existing

        agent = await _spawn_agent(omoios_session_id)
        _registry[omoios_session_id] = agent
        return agent


async def close(omoios_session_id: str) -> None:
    agent = _registry.pop(omoios_session_id, None)
    if agent is not None:
        await agent.close()


async def close_all() -> None:
    for sid in list(_registry.keys()):
        try:
            await close(sid)
        except Exception:  # noqa: BLE001
            pass


def is_enabled() -> bool:
    """Return True iff the sandboxed-agent feature flag is on AND
    provider is Modal."""
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
    )

    # The spawner only writes opencode.json / auth.json when an
    # `env_version` with credentials is supplied. Chat-mode SDK-direct
    # sessions don't have one, so we render the configs inline here using
    # the backend's own LLM_API_KEY. This mirrors `modal_sandbox_smoke.py`
    # mode=llm (lines 210-228).
    await _write_opencode_configs(spawner, sandbox_id, api_key=api_key)

    return ModalSandboxedAgent(
        omoios_session_id=omoios_session_id,
        sandbox_id=sandbox_id,
        spawner=spawner,
        provider="fireworks-ai",
        model=_DEFAULT_OPENCODE_MODEL,
        spawned_at=time.time(),
    )


async def _write_opencode_configs(
    spawner: Any, sandbox_id: str, *, api_key: str
) -> None:
    """Render opencode.json + auth.json directly into the sandbox.

    Same shape as `scripts/modal_sandbox_smoke.py` lines 210-228.
    """
    opencode_json = json.dumps(
        {
            "$schema": "https://opencode.ai/config.json",
            "model": _DEFAULT_OPENCODE_MODEL,
        }
    ).encode("utf-8")
    auth_json = json.dumps({"fireworks-ai": {"type": "api", "key": api_key}}).encode(
        "utf-8"
    )

    await spawner.exec(sandbox_id, "mkdir", "-p", "/root/.config/opencode")
    await spawner.exec(sandbox_id, "mkdir", "-p", "/root/.local/share/opencode")
    await spawner.upload_file(
        sandbox_id, "/root/.config/opencode/opencode.json", opencode_json
    )
    await spawner.upload_file(
        sandbox_id, "/root/.local/share/opencode/auth.json", auth_json
    )


def _resolve_llm_api_key() -> Optional[str]:
    """Return the API key for opencode's `fireworks-ai` provider.

    Prefer FIREWORKS_API_KEY (matches the smoke pattern), fall back to
    LLM_API_KEY (the platform-wide knob). The proof-of-life lane is
    Fireworks-only, so both names point at the same key in practice.
    """
    return os.environ.get("FIREWORKS_API_KEY") or os.environ.get("LLM_API_KEY")


# ─── stdout parsing ──────────────────────────────────────────────────────────


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _extract_opencode_reply(stdout: str) -> str:
    """Trim opencode's stdout to the actual reply body.

    With `--log-level ERROR` opencode's stdout is the model's reply text
    on success, occasionally prefixed with build/version banners. Strip
    leading banner lines that look like `> opencode vX.Y.Z` or empty
    framing lines, then collapse trailing whitespace. We do NOT try to
    strip ANSI codes — opencode emits plain text with `--print-logs
    --log-level ERROR`.
    """
    if not stdout:
        return ""
    lines = stdout.splitlines()
    cleaned: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        # Drop obvious framing/banner lines but keep blank lines in the
        # middle of a reply intact.
        if not cleaned and not stripped:
            continue
        if not cleaned and stripped.startswith(">"):
            # `> opencode vX.Y.Z` — opencode banner.
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned).rstrip()
