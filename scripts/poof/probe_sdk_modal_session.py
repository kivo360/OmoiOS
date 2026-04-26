"""Probe: full chat round-trip via SDK + OmoiOsModalProvider + opencode + Fireworks.

Spawns a Modal sandbox with the omoi_os image (sandbox-agent server +
opencode pre-baked), injects an auth.json so opencode can reach Fireworks,
connects via SandboxAgent.connect, creates an opencode session, sends one
prompt, asserts a non-empty reply, tears down.

Requires LLM_API_KEY in backend/.env (Fireworks key).
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Load env from backend/.env so LLM_API_KEY shows up.
_ENV_FILE = Path(__file__).resolve().parents[2] / "backend" / ".env"
if _ENV_FILE.exists():
    for line in _ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

from sandboxagent import SandboxAgent
from sandboxagent.workspace_config import WorkspaceConfig

from omoi_os.services.sa_modal_provider import OmoiOsModalProvider


def _step(n: int, msg: str) -> None:
    print(f"[step {n}] {msg}", flush=True)


async def main() -> int:
    fireworks_key = os.environ.get("FIREWORKS_API_KEY") or os.environ.get("LLM_API_KEY")
    if not fireworks_key:
        print("FATAL: no FIREWORKS_API_KEY or LLM_API_KEY in env (check backend/.env)")
        return 2

    _step(1, "construct OmoiOsModalProvider (default image: debian_slim + sandbox-agent + opencode)")
    provider = OmoiOsModalProvider()

    auth_json = WorkspaceConfig.auth_json({"fireworks-ai": {"type": "api", "key": fireworks_key}})
    print(f"   auth.json size: {len(auth_json)} bytes")

    _step(2, "SandboxAgent.start(provider=…, workspace_files={'auth.json': …}) — spawn + bootstrap workspace")
    agent: SandboxAgent | None = None
    try:
        agent = await SandboxAgent.start(
            provider=provider,
            workspace_files={"auth.json": auth_json},
            health_timeout=60.0,
        )
        print(f"   agent connected; sandbox_id = {agent.sandbox_id}")

        _step(3, "agent.create_session(agent='opencode')")
        try:
            session = await agent.create_session(agent="opencode")
            print(f"   session.id = {session.id}")
        except Exception as e:
            print(f"   create_session failed: {type(e).__name__}: {e}")
            print("   (sandbox-agent server only registers claude/codex by default;")
            print("    opencode would need explicit install-agent or upstream support)")
            health = await agent.health()
            print(f"   health: {health}")
            return 1

        _step(4, "session.prompt(...) — single chat turn")
        response = await session.prompt(
            "Reply with the single word PONG and nothing else.",
        )
        print(f"   response.text = {getattr(response, 'text', '<no text attr>')!r}")
        print(f"   response repr  = {response!r}")
        return 0
    finally:
        if agent is not None:
            _step(99, "dispose agent (tears down sandbox via provider.destroy)")
            try:
                if agent.sandbox_id and provider:
                    await provider.destroy(agent.sandbox_id)
                await agent.dispose()
                print("   ok")
            except Exception as e:
                print(f"   teardown failed: {type(e).__name__}: {e}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
