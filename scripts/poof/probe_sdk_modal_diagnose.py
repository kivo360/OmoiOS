"""Diagnostic: spawn an idle Modal sandbox using the rivetdev/sandbox-agent
image, then exec inside to check (a) the binary exists, (b) it can run, and
(c) what happens when we start it manually.

Helps explain why probe_sdk_modal_spawn.py spawns the sandbox but /v1/health
is unreachable.
"""

from __future__ import annotations

import asyncio
import sys

import modal

from sandboxagent.providers.shared import DEFAULT_SANDBOX_AGENT_IMAGE


def _step(n: int, msg: str) -> None:
    print(f"[step {n}] {msg}", flush=True)


async def main() -> int:
    _step(1, f"build image from registry: {DEFAULT_SANDBOX_AGENT_IMAGE}")
    image = modal.Image.from_registry(DEFAULT_SANDBOX_AGENT_IMAGE)

    _step(2, "lookup app omoi-os-agents")
    app = await asyncio.to_thread(
        modal.App.lookup, "omoi-os-agents", create_if_missing=True
    )

    _step(3, "spawn sandbox running 'sleep infinity' (keep alive for diagnostics)")
    sandbox = await asyncio.to_thread(
        lambda: modal.Sandbox.create(
            "sleep",
            "infinity",
            app=app,
            image=image,
            encrypted_ports=[3000],
            timeout=300,
        )
    )
    sandbox_id = sandbox.object_id
    print(f"   sandbox_id = {sandbox_id}")

    try:
        _step(4, "exec: which sandbox-agent")
        proc = await asyncio.to_thread(
            lambda: sandbox.exec("which", "sandbox-agent")
        )
        # exec returns a ContainerProcess; read stdout/stderr
        stdout = await asyncio.to_thread(proc.stdout.read)
        stderr = await asyncio.to_thread(proc.stderr.read)
        rc = await asyncio.to_thread(proc.wait)
        print(f"   rc={rc}, stdout={stdout!r}, stderr={stderr!r}")

        _step(5, "exec: sandbox-agent --version")
        proc = await asyncio.to_thread(
            lambda: sandbox.exec("sandbox-agent", "--version")
        )
        stdout = await asyncio.to_thread(proc.stdout.read)
        stderr = await asyncio.to_thread(proc.stderr.read)
        rc = await asyncio.to_thread(proc.wait)
        print(f"   rc={rc}, stdout={stdout!r}, stderr={stderr!r}")

        _step(6, "exec: sandbox-agent server --help (verify CLI shape)")
        proc = await asyncio.to_thread(
            lambda: sandbox.exec("sandbox-agent", "server", "--help")
        )
        stdout = await asyncio.to_thread(proc.stdout.read)
        stderr = await asyncio.to_thread(proc.stderr.read)
        rc = await asyncio.to_thread(proc.wait)
        print(f"   rc={rc}")
        print(f"   stdout: {stdout[:500] if stdout else '(empty)'}")
        print(f"   stderr: {stderr[:300] if stderr else '(empty)'}")

        _step(7, "exec: ls -la /usr/local/bin/ | grep sandbox-agent")
        proc = await asyncio.to_thread(
            lambda: sandbox.exec("sh", "-c", "ls -la /usr/local/bin/ | grep -i sandbox || ls /sandbox-agent* 2>/dev/null || find / -name 'sandbox-agent' 2>/dev/null | head -5")
        )
        stdout = await asyncio.to_thread(proc.stdout.read)
        rc = await asyncio.to_thread(proc.wait)
        print(f"   rc={rc}, stdout={stdout!r}")

    finally:
        _step(99, f"teardown: sandbox.terminate({sandbox_id})")
        try:
            await asyncio.to_thread(sandbox.terminate)
            print("   destroyed OK")
        except Exception as e:
            print(f"   destroy failed: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
