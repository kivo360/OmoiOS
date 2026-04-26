"""Probe: spawn sandbox, then directly curl ACP endpoints to see what the
server actually expects for agent="opencode" sessions. Bypasses the SDK
entirely to isolate where the request goes wrong.
"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx
import modal

from sandboxagent.providers.shared import SANDBOX_AGENT_INSTALL_SCRIPT


def _step(n: int, msg: str) -> None:
    print(f"[step {n}] {msg}", flush=True)


async def main() -> int:
    image = (
        modal.Image.debian_slim()
        .apt_install("curl", "ca-certificates", "git")
        .run_commands(
            f"curl -fsSL {SANDBOX_AGENT_INSTALL_SCRIPT} | sh",
            "mkdir -p /root/.local/share/opencode /root/.config/opencode",
            "curl -fsSL https://opencode.ai/install | bash",
        )
        .env({"PATH": "/root/.opencode/bin:/usr/local/bin:/usr/bin:/bin"})
    )
    app = await modal.App.lookup.aio("omoi-os-agents", create_if_missing=True)

    _step(1, "spawn sandbox running sandbox-agent server on :3000")
    sandbox = await modal.Sandbox.create.aio(
        "sandbox-agent", "server", "--no-token", "--host", "0.0.0.0", "--port", "3000",
        app=app, image=image, timeout=300, encrypted_ports=[3000],
    )
    print(f"   sandbox_id = {sandbox.object_id}")

    try:
        tunnels = await sandbox.tunnels.aio()
        url = tunnels[3000].url
        print(f"   url = {url}")

        async with httpx.AsyncClient(timeout=30) as c:
            # Wait for /v1/health
            for i in range(30):
                try:
                    r = await c.get(f"{url}/v1/health")
                    if r.status_code == 200:
                        print(f"   /v1/health ready (attempt {i+1})")
                        break
                except Exception:
                    pass
                await asyncio.sleep(2)

            _step(2, "GET /v1/acp — list ACP server_ids")
            r = await c.get(f"{url}/v1/acp")
            print(f"   {r.status_code}: {r.text[:500]}")

            _step(3, "GET /v1/agents — list agents")
            r = await c.get(f"{url}/v1/agents")
            print(f"   {r.status_code}: {r.text[:800]}")

            _step(4, "POST /v1/acp/default?agent=opencode with initialize")
            init_body = {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-18",
                    "clientCapabilities": {},
                    "clientInfo": {"name": "curl-probe", "version": "v1"},
                },
            }
            r = await c.post(f"{url}/v1/acp/default", params={"agent": "opencode"}, json=init_body)
            print(f"   {r.status_code}: {r.text[:1000]}")

            _step(5, "Same but with agent=claude")
            r = await c.post(f"{url}/v1/acp/default-claude", params={"agent": "claude"}, json=init_body)
            print(f"   {r.status_code}: {r.text[:1000]}")

            _step(6, "Try without clientCapabilities key")
            init_body_minimal = {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-03-18"},
            }
            r = await c.post(f"{url}/v1/acp/min-test", params={"agent": "opencode"}, json=init_body_minimal)
            print(f"   {r.status_code}: {r.text[:1000]}")

            _step(7, "session/new with various param shapes against an initialized server")
            sid = "sess-test"
            r = await c.post(f"{url}/v1/acp/{sid}", params={"agent": "opencode"}, json={
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": 1, "clientCapabilities": {}},
            })
            print(f"   initialize: {r.status_code}: {r.text[:300]}")

            r = await c.post(f"{url}/v1/acp/{sid}", json={
                "jsonrpc": "2.0", "id": 2, "method": "session/new",
                "params": {"agent": "opencode", "cwd": "/root", "mcpServers": []},
            })
            session_id = r.json().get("result", {}).get("sessionId")
            print(f"   session/new -> sessionId={session_id}")

            _step(8, "session/prompt — try various param shapes to find what the server accepts")
            for params in [
                {"sessionId": session_id, "prompt": "hello"},
                {"sessionId": session_id, "prompt": [{"type": "text", "text": "hello"}]},
                {"sessionId": session_id, "prompt": [{"type": "text", "text": "hello"}], "streaming": False},
                {"sessionId": session_id, "messages": [{"type": "text", "text": "hello"}]},
                {"sessionId": session_id, "parts": [{"type": "text", "text": "hello"}]},
                {"sessionId": session_id, "content": "hello"},
                {"sessionId": session_id, "prompt": {"text": "hello"}},
            ]:
                r = await c.post(f"{url}/v1/acp/{sid}", json={
                    "jsonrpc": "2.0", "id": 99, "method": "session/prompt", "params": params,
                })
                # Trim body to find the actual error inputs
                body = r.text[:500]
                shape = list(params.keys())
                print(f"   {shape}: {r.status_code}: {body}")

    finally:
        _step(99, "terminate")
        try:
            await sandbox.terminate.aio()
            print("   ok")
        except Exception as e:
            print(f"   terminate failed: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
