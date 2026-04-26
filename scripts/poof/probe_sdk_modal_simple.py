"""Probe (simpler): figure out why rivetdev/sandbox-agent image kills the
sandbox immediately. Tests two hypotheses:

  H1: rivetdev image has an ENTRYPOINT that conflicts with our `sleep infinity`
      args — the args are interpreted as arguments to the entrypoint, which
      fails and exits, killing the sandbox.
  H2: Image is fine but our exec/stream API usage is wrong.

This probe uses a plain debian image first to validate the basic spawn +
exec + stream flow. If that works, we know the issue is the rivetdev image
specifically.
"""

from __future__ import annotations

import asyncio
import sys

import modal


def _step(n: int, msg: str) -> None:
    print(f"[step {n}] {msg}", flush=True)


async def main() -> int:
    _step(1, "build plain debian_slim image (control case)")
    image = modal.Image.debian_slim()

    _step(2, "lookup app")
    app = await asyncio.to_thread(
        modal.App.lookup, "omoi-os-agents", create_if_missing=True
    )

    _step(3, "spawn sandbox: sleep infinity")
    sandbox = await asyncio.to_thread(
        lambda: modal.Sandbox.create(
            "sleep",
            "infinity",
            app=app,
            image=image,
            timeout=120,
        )
    )
    sandbox_id = sandbox.object_id
    print(f"   sandbox_id = {sandbox_id}")

    try:
        await asyncio.sleep(2)  # let sandbox settle

        _step(4, "exec: echo hello (use wait_with_output via async)")
        proc = await asyncio.to_thread(lambda: sandbox.exec("echo", "hello"))
        # Modal sync API: read stdout fully via .read()
        rc = await asyncio.to_thread(proc.wait)
        out = proc.stdout.read()
        err = proc.stderr.read()
        print(f"   rc={rc}, stdout={out!r}, stderr={err!r}")

        _step(5, "exec: uname -a")
        proc = await asyncio.to_thread(lambda: sandbox.exec("uname", "-a"))
        rc = await asyncio.to_thread(proc.wait)
        out = proc.stdout.read()
        print(f"   rc={rc}, stdout={out!r}")

        _step(6, "exec: which curl (does debian_slim have curl?)")
        proc = await asyncio.to_thread(lambda: sandbox.exec("which", "curl"))
        rc = await asyncio.to_thread(proc.wait)
        out = proc.stdout.read()
        print(f"   rc={rc}, stdout={out!r}")

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
