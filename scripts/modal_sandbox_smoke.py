#!/usr/bin/env python3
# Bare Modal-sandbox smoke test — bypasses orchestrator + spawner glue.
#
# Three modes:
#   bare    -> just python+node primitives in a fresh sandbox
#   install -> bare + verify primitives still work after opencode install
#   llm     -> install + write configs + real Kimi LLM call
#
# Modes use a pre-baked image (`omoi-smoke:opencode`) — opencode is
# installed at IMAGE-BUILD time, then cached by Modal. First run pays
# ~30s for the image build; subsequent runs reuse the cache and skip
# the install entirely. The "init" phase forces the build so timing
# of later steps reflects only the work, not the cold-start.
#
# Usage:
#   .venv/bin/python scripts/modal_sandbox_smoke.py                   # bare
#   .venv/bin/python scripts/modal_sandbox_smoke.py --mode install
#   .venv/bin/python scripts/modal_sandbox_smoke.py --mode llm
#   .venv/bin/python scripts/modal_sandbox_smoke.py --keep            # leave sandbox up

from __future__ import annotations

import argparse
import os
import sys
import time

print("  ▸ modal-smoke booting…", flush=True)
T0 = time.perf_counter()

import modal  # noqa: E402

print(
    f"  ▸ modal sdk loaded ({(time.perf_counter() - T0) * 1000:.0f}ms)",
    flush=True,
)

IMAGE_REF = "nikolaik/python-nodejs:python3.12-nodejs22"
APP_NAME = "omoi-smoke-1off"


# ─── timing helpers ─────────────────────────────────────────────────────────


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def _print_step(name: str, ms: float, status: str = "✓", detail: str = "") -> None:
    color = {"✓": "\033[32m", "✗": "\033[31m", "▸": "\033[36m", "·": "\033[90m"}.get(
        status, ""
    )
    reset = "\033[0m"
    suffix = f"  {detail}" if detail else ""
    print(
        f"  {color}{status}{reset} {name:<28}  {ms:>6.0f}ms{suffix}", flush=True
    )


def _run_step(name: str, fn) -> object:
    """Run a callable with a label and timing; non-exec work."""
    t = time.perf_counter()
    try:
        out = fn()
        _print_step(name, _ms(t))
        return out
    except Exception as exc:  # noqa: BLE001
        _print_step(name, _ms(t), "✗", f"{type(exc).__name__}: {exc}")
        raise


def _run_exec(name: str, sandbox, *cmd, expect_stdout: bool = True) -> tuple[str, str, int]:
    """Run a command in the sandbox, BLOCK until it exits, then capture
    stdout/stderr. The clock stops AFTER wait() so the timing reflects
    actual command duration, not just dispatch latency."""
    t = time.perf_counter()
    try:
        proc = sandbox.exec(*cmd)
        # Read FIRST so we drain the pipe and don't deadlock on a full
        # buffer; then wait for the process to finish.
        stdout = proc.stdout.read()
        stderr = proc.stderr.read()
        proc.wait()
        rc = proc.returncode
        ms = _ms(t)
        if rc != 0:
            _print_step(name, ms, "✗", f"rc={rc}")
            if stdout.strip():
                print(f"      stdout: {stdout.strip()[:200]!r}", flush=True)
            if stderr.strip():
                print(f"      stderr: {stderr.strip()[:200]!r}", flush=True)
            return stdout, stderr, rc
        detail = ""
        if expect_stdout and stdout.strip():
            detail = f"  → {stdout.strip()[:60]!r}"
        _print_step(name, ms, "✓", detail)
        return stdout, stderr, rc
    except Exception as exc:  # noqa: BLE001
        _print_step(name, _ms(t), "✗", f"{type(exc).__name__}: {exc}")
        raise


# ─── image variants ─────────────────────────────────────────────────────────


def _bare_image() -> modal.Image:
    return modal.Image.from_registry(IMAGE_REF).run_commands(
        "mkdir -p /root/.local/share/opencode /root/.config/opencode"
    )


def _opencode_image() -> modal.Image:
    """Image with opencode pre-installed at build time. Modal caches
    this by content hash — first build is slow (~30s), subsequent
    runs skip straight to sandbox.create."""
    return modal.Image.from_registry(IMAGE_REF).run_commands(
        "mkdir -p /root/.local/share/opencode /root/.config/opencode",
        # Install + verify in the same layer so a broken install surfaces
        # at image-build time, not at first sandbox.exec.
        "curl -fsSL https://opencode.ai/install | bash",
        "/root/.opencode/bin/opencode --version",
    )


# ─── main ───────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--mode",
        choices=("bare", "install", "llm"),
        default="bare",
    )
    p.add_argument(
        "--keep",
        action="store_true",
        help="leave sandbox running on exit (for manual inspection)",
    )
    args = p.parse_args()

    needs_opencode = args.mode in ("install", "llm")

    app = _run_step(
        "lookup app",
        lambda: modal.App.lookup(APP_NAME, create_if_missing=True),
    )

    # ─── init: build/cache the image upfront ─────────────────────────────
    # Modal hashes the image spec; if we've built this exact recipe
    # before, this is instant. Spawning a throwaway sandbox forces
    # the build to happen NOW (with visible timing) instead of being
    # silently amortized into the first real sandbox.create later.
    if needs_opencode:
        print("  ▸ init: ensuring opencode image is cached", flush=True)
        t = time.perf_counter()
        warm_image = _opencode_image()
        warm_sb = modal.Sandbox.create(
            "true", app=app, image=warm_image, timeout=120
        )
        warm_sb.wait()
        warm_sb.terminate()
        _print_step("init: image build/cache", _ms(t))
        image = warm_image
    else:
        image = _run_step("init: bare image", _bare_image)

    sandbox = _run_step(
        "create sandbox",
        lambda: modal.Sandbox.create(
            "sleep", "infinity", app=app, image=image, timeout=600
        ),
    )
    print(f"      sandbox id: {sandbox.object_id}", flush=True)

    try:
        # ─── primitives ──────────────────────────────────────────────────
        _run_exec("python -c hello", sandbox, "python3", "-c", "print('hello')")
        _run_step(
            "write /tmp/hello.py",
            lambda: sandbox.filesystem.write_bytes(
                b"import sys; print(sys.version_info[:3])\n", "/tmp/hello.py"
            ),
        )
        _run_exec("run /tmp/hello.py", sandbox, "python3", "/tmp/hello.py")
        _run_exec("node -e", sandbox, "node", "-e", "console.log('hello-node')")

        if args.mode in ("install", "llm"):
            _run_exec(
                "opencode --version (pre-baked)",
                sandbox,
                "/root/.opencode/bin/opencode",
                "--version",
            )
            # Re-verify primitives after opencode is in the image.
            _run_exec(
                "python -c after install",
                sandbox,
                "python3",
                "-c",
                "print('python-still-works')",
            )

        if args.mode == "llm":
            fw = os.environ.get("FIREWORKS_API_KEY")
            if not fw:
                _print_step("llm step", 0, "✗", "FIREWORKS_API_KEY not set")
                return 1

            opencode_json = (
                b'{"$schema":"https://opencode.ai/config.json",'
                b'"model":"fireworks-ai/accounts/fireworks/routers/kimi-k2p5-turbo"}'
            )
            auth_json = (
                b'{"fireworks-ai":{"type":"api","key":"' + fw.encode() + b'"}}'
            )
            _run_step(
                "write opencode.json",
                lambda: sandbox.filesystem.write_bytes(
                    opencode_json, "/root/.config/opencode/opencode.json"
                ),
            )
            _run_step(
                "write auth.json",
                lambda: sandbox.filesystem.write_bytes(
                    auth_json, "/root/.local/share/opencode/auth.json"
                ),
            )
            # Network sanity first — verify the sandbox can reach Fireworks.
            _run_exec(
                "curl fireworks /models",
                sandbox,
                "bash",
                "-lc",
                "curl -sS -o /dev/null -w 'http=%{http_code} time=%{time_total}\\n' "
                "--max-time 10 -H \"Authorization: Bearer ${FIREWORKS_API_KEY:-none}\" "
                "https://api.fireworks.ai/inference/v1/models",
            )
            # opencode run with stdin closed + hard timeout — local takes 5s,
            # so 60s is generous. Anything longer is a hang.
            stdout, stderr, rc = _run_exec(
                "opencode run (Kimi)",
                sandbox,
                "bash",
                "-lc",
                "cd /tmp && timeout 60 /root/.opencode/bin/opencode run "
                "--print-logs --log-level ERROR "
                "--dangerously-skip-permissions "
                "'Reply with exactly: SBOXOK' < /dev/null",
                expect_stdout=False,  # we'll print full body below
            )
            ok = rc == 0 and "SBOXOK" in stdout
            print(
                f"  {'✓' if ok else '✗'} kimi reply contains SBOXOK: {ok}",
                flush=True,
            )
            print("      ─── opencode stdout ───", flush=True)
            for line in stdout.strip().splitlines():
                print(f"      {line}", flush=True)
            if stderr.strip():
                print("      ─── opencode stderr ───", flush=True)
                for line in stderr.strip().splitlines()[:20]:
                    print(f"      {line}", flush=True)

    finally:
        if not args.keep:
            _run_step("terminate sandbox", lambda: sandbox.terminate())
        else:
            print(f"  · leaving {sandbox.object_id} running (--keep)", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
