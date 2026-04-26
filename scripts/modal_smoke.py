#!/usr/bin/env python3
"""Standalone Modal-backed sandbox smoke test.

Mirrors the daytona_allocation phase from `smoke_agent_platform.py` but
goes through OmoiOS's `ModalSpawnerService` + `ModalProvider` to prove
the new path is wired up correctly.

Phases (one PASS each is the goal):

    1. provider_init      — factory dispatches on settings.sandbox.provider
    2. spawn              — ModalProvider.spawn_for_task → live sandbox
    3. exec_echo          — exec a command, capture stdout
    4. exec_egress        — verify outbound network reaches api.github.com
    5. file_roundtrip     — write + read a file in the sandbox FS
    6. terminate          — explicit teardown

Prereqs:
    MODAL_TOKEN_ID  + MODAL_TOKEN_SECRET in env (or `~/.modal.toml`)
    SANDBOX_PROVIDER=modal in env (or `sandbox.provider: modal` in config)

Usage:
    uv run --project backend python scripts/modal_smoke.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))


GREEN, RED, YELLOW, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def _ok(msg: str) -> None:
    print(f"{GREEN}✔{RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"{RED}✖{RESET} {msg}")


def _info(msg: str) -> None:
    print(f"{YELLOW}▸{RESET} {msg}")


async def main() -> int:
    # Make sure the factory routes to Modal regardless of the YAML config
    # this script is launched against.
    os.environ.setdefault("SANDBOX_PROVIDER", "modal")

    failures: list[str] = []

    # 1. provider_init
    try:
        from omoi_os.services.sandbox_factory import create_sandbox_provider
        from omoi_os.services.modal_provider import ModalProvider

        provider = create_sandbox_provider(db=None, event_bus=None)
        if not isinstance(provider, ModalProvider):
            raise RuntimeError(
                f"factory returned {type(provider).__name__}; expected ModalProvider"
            )
        _ok(f"provider_init: {type(provider).__name__}")
    except Exception as exc:
        _fail(f"provider_init: {type(exc).__name__}: {exc}")
        return 1

    # 2. spawn
    sandbox_id: str | None = None
    started = time.perf_counter()
    try:
        from omoi_os.services.sandbox_provider import SandboxResult

        result: SandboxResult = await provider.spawn_for_task(
            task_id=f"modal-smoke-{os.urandom(4).hex()}",
            agent_id="smoke-agent",
            phase_id="PHASE_SMOKE",
            env_vars={"SMOKE_TEST": "1"},
            runtime="claude",
            execution_mode="implementation",
        )
        sandbox_id = result.sandbox_id
        elapsed = time.perf_counter() - started
        _ok(
            f"spawn: id={sandbox_id} status={result.status} "
            f"({elapsed:.1f}s)"
        )
    except Exception as exc:
        _fail(f"spawn: {type(exc).__name__}: {exc}")
        return 1

    # The remaining phases drive the spawner directly so we exercise the
    # exec/fs surface, not just create+terminate.
    from omoi_os.services.modal_spawner import get_modal_spawner

    spawner = get_modal_spawner()

    # 3. exec_echo
    try:
        result = await spawner.exec(sandbox_id, "echo", "hello-from-modal")
        out = (result.get("stdout") or "").strip()
        if "hello-from-modal" not in out:
            raise RuntimeError(f"unexpected stdout: {out!r}")
        _ok(f"exec_echo: stdout={out!r}")
    except Exception as exc:
        _fail(f"exec_echo: {type(exc).__name__}: {exc}")
        failures.append("exec_echo")

    # 4. exec_egress
    try:
        result = await spawner.exec(
            sandbox_id,
            "sh",
            "-c",
            "curl -s -o /dev/null -w '%{http_code}' https://api.github.com",
        )
        code = (result.get("stdout") or "").strip()
        if not (code.startswith("2") or code.startswith("3")):
            raise RuntimeError(f"non-success status: {code!r}")
        _ok(f"exec_egress: github responded {code}")
    except Exception as exc:
        _fail(f"exec_egress: {type(exc).__name__}: {exc}")
        failures.append("exec_egress")

    # 5. file_roundtrip
    try:
        path = "/tmp/omoios-modal-smoke.txt"
        payload = b"hello from modal smoke\n"
        await spawner.upload_file(sandbox_id, path, payload)
        readback = await spawner.download_file(sandbox_id, path)
        if readback != payload:
            raise RuntimeError(f"mismatch: wrote {payload!r}, read {readback!r}")
        _ok(f"file_roundtrip: {len(payload)} bytes via {path}")
    except Exception as exc:
        _fail(f"file_roundtrip: {type(exc).__name__}: {exc}")
        failures.append("file_roundtrip")

    # 6. terminate
    try:
        await provider.terminate_sandbox(sandbox_id)
        _ok("terminate")
    except Exception as exc:
        _fail(f"terminate: {type(exc).__name__}: {exc}")
        failures.append("terminate")

    print()
    if failures:
        _info(f"{len(failures)} phase(s) failed: {', '.join(failures)}")
        return 1
    _ok("all phases pass — Modal sandbox provider is wired up")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
