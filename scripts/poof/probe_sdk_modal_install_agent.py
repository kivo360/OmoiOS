"""Probe: spawn sandbox, then run sandbox-agent install-agent opencode
inside it (post-spawn) before connecting via SDK.

Tests whether install-agent works at runtime (not image-build time) and
whether opencode is registered after install.
"""

from __future__ import annotations

import asyncio
import sys

import modal


def _step(n: int, msg: str) -> None:
    print(f"[step {n}] {msg}", flush=True)


async def main() -> int:
    _step(1, "build minimal image: debian_slim + sandbox-agent + opencode")
    from sandboxagent.providers.shared import SANDBOX_AGENT_INSTALL_SCRIPT

    image = (
        modal.Image.debian_slim()
        .apt_install("curl", "ca-certificates", "git")
        .run_commands(
            f"curl -fsSL {SANDBOX_AGENT_INSTALL_SCRIPT} | sh",
            "sandbox-agent --version",
            "mkdir -p /root/.local/share/opencode /root/.config/opencode",
            "curl -fsSL https://opencode.ai/install | bash",
            "/root/.opencode/bin/opencode --version",
        )
        .env({"PATH": "/root/.opencode/bin:/usr/local/bin:/usr/bin:/bin"})
    )

    _step(2, "spawn idle sandbox (sleep infinity) — install-agent will run inside")
    app = await modal.App.lookup.aio("omoi-os-agents", create_if_missing=True)
    sandbox = await modal.Sandbox.create.aio(
        "sleep", "infinity",
        app=app, image=image, timeout=180,
    )
    print(f"   sandbox_id = {sandbox.object_id}")

    try:
        _step(3, "exec: which opencode (verify PATH)")
        proc = await sandbox.exec.aio("sh", "-c", "echo PATH=$PATH; which opencode")
        await proc.wait.aio()
        out = await proc.stdout.read.aio()
        print(f"   stdout: {out!r}")

        _step(4, "exec: sandbox-agent install-agent opencode")
        proc = await sandbox.exec.aio("sh", "-c", "sandbox-agent install-agent opencode 2>&1")
        rc = await proc.wait.aio()
        out = await proc.stdout.read.aio()
        print(f"   rc={rc}, stdout: {out[:1000]!r}")

        _step(5, "exec: sandbox-agent install-agent --all")
        proc = await sandbox.exec.aio("sh", "-c", "sandbox-agent install-agent --all 2>&1")
        rc = await proc.wait.aio()
        out = await proc.stdout.read.aio()
        print(f"   rc={rc}, stdout: {out[:1000]!r}")
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
