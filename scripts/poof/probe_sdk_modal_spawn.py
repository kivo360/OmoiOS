"""Probe: spawn a Modal sandbox via the SDK + OmoiOsModalProvider, hit
sandbox-agent's /v1/health, tear down.

Validates that the sandbox-agent-sdk modal provider rewrite (commit bcdbcbe
in kivo360/sandbox-agent-python) plus the OmoiOsModalProvider subclass
actually work end-to-end against live Modal infrastructure. No opencode,
no LLM — just sandbox-agent server in a Modal sandbox.

Run:
    cd backend && uv run python ../scripts/poof/probe_sdk_modal_spawn.py

Requires Modal auth (either ~/.modal.toml or MODAL_TOKEN_ID + MODAL_TOKEN_SECRET).
Spends real Modal credits — sandbox lives ~30-60s before teardown.
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

import httpx

from sandboxagent.providers.shared import DEFAULT_SANDBOX_AGENT_IMAGE


def _step(n: int, msg: str) -> None:
    print(f"[step {n}] {msg}", flush=True)


async def main() -> int:
    _step(1, "let OmoiOsModalProvider build its own image (debian_slim + sandbox-agent + opencode)")

    _step(2, "construct OmoiOsModalProvider with default image build")
    from omoi_os.services.sa_modal_provider import OmoiOsModalProvider

    provider = OmoiOsModalProvider()
    print(f"   provider.app_name = {provider.app_name}")
    print(f"   provider.agent_port = {provider.agent_port}")

    sandbox_id: str | None = None
    try:
        _step(3, "provider.create() → spawn Modal sandbox running sandbox-agent server")
        sandbox_id = await provider.create()
        print(f"   sandbox_id = {sandbox_id}")

        _step(4, "provider.get_url() → resolve public tunnel URL for agent_port")
        url = await provider.get_url(sandbox_id)
        print(f"   url = {url}")

        _step(5, "HTTP poll {url}/v1/health (15 attempts, 2s spacing → 30s timeout)")
        async with httpx.AsyncClient(timeout=15) as client:
            for attempt in range(1, 16):
                try:
                    resp = await client.get(f"{url}/v1/health")
                    if resp.status_code == 200:
                        body = resp.text[:200]
                        print(f"   attempt {attempt}: OK 200 — body: {body!r}")
                        _step(6, "verify a basic API surface: GET /v1/agents")
                        agents_resp = await client.get(f"{url}/v1/agents")
                        print(
                            f"   /v1/agents → {agents_resp.status_code}, body: {agents_resp.text[:300]!r}"
                        )
                        return 0
                    else:
                        print(f"   attempt {attempt}: HTTP {resp.status_code}")
                except (httpx.RequestError, httpx.HTTPError) as e:
                    print(f"   attempt {attempt}: {type(e).__name__}: {e}")
                await asyncio.sleep(2)
            print("   FAIL: /v1/health never returned 200 within 30s")
            return 1
    finally:
        if sandbox_id is not None:
            _step(99, f"teardown: provider.destroy({sandbox_id})")
            try:
                await provider.destroy(sandbox_id)
                print("   destroyed OK")
            except Exception as e:  # noqa: BLE001 — cleanup best-effort
                print(f"   destroy failed (continuing): {type(e).__name__}: {e}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
