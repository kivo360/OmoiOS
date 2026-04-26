"""Probe: try installing sandbox-agent in a clean Modal sandbox to verify
the install script + binary actually works. Goal: replace the broken
rivetdev/sandbox-agent registry image with a self-built clean image in
OmoiOsModalProvider.build_omoi_modal_image().
"""

from __future__ import annotations

import asyncio
import sys

import modal

from sandboxagent.providers.shared import (
    SANDBOX_AGENT_INSTALL_SCRIPT,
    SANDBOX_AGENT_VERSION,
)


def _step(n: int, msg: str) -> None:
    print(f"[step {n}] {msg}", flush=True)


async def main() -> int:
    _step(1, f"install URL: {SANDBOX_AGENT_INSTALL_SCRIPT}")
    print(f"   target version: {SANDBOX_AGENT_VERSION}")

    _step(2, "build image: debian_slim + curl + sandbox-agent install")
    image = (
        modal.Image.debian_slim()
        .apt_install("curl", "ca-certificates")
        .run_commands(
            f"curl -fsSL {SANDBOX_AGENT_INSTALL_SCRIPT} | sh",
            "ls -la /usr/local/bin/sandbox-agent /root/.local/bin/sandbox-agent /usr/bin/sandbox-agent 2>/dev/null || true",
            "which sandbox-agent || find / -name 'sandbox-agent' -type f 2>/dev/null | head -5",
        )
    )

    _step(3, "lookup app")
    app = await asyncio.to_thread(
        modal.App.lookup, "omoi-os-agents", create_if_missing=True
    )

    _step(4, "spawn sandbox: sleep infinity")
    sandbox = await asyncio.to_thread(
        lambda: modal.Sandbox.create(
            "sleep", "infinity", app=app, image=image, timeout=120,
        )
    )
    print(f"   sandbox_id = {sandbox.object_id}")

    try:
        _step(5, "exec: which sandbox-agent")
        proc = await asyncio.to_thread(lambda: sandbox.exec("sh", "-c", "which sandbox-agent || find / -name 'sandbox-agent' -type f 2>/dev/null | head -3"))
        await asyncio.to_thread(proc.wait)
        out = proc.stdout.read()
        err = proc.stderr.read()
        print(f"   stdout: {out!r}")
        print(f"   stderr: {err[:200] if err else ''!r}")

        _step(6, "exec: sandbox-agent --version (or print PATH if missing)")
        proc = await asyncio.to_thread(lambda: sandbox.exec("sh", "-c", "sandbox-agent --version 2>&1 || (echo MISSING; echo PATH=$PATH)"))
        await asyncio.to_thread(proc.wait)
        out = proc.stdout.read()
        print(f"   stdout: {out!r}")

    finally:
        _step(99, "terminate")
        try:
            await asyncio.to_thread(sandbox.terminate)
            print("   ok")
        except Exception as e:
            print(f"   terminate failed: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
