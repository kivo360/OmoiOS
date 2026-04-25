#!/usr/bin/env python3
"""Stage 2: run OpenCode *inside* a Daytona sandbox and drive it from outside.

Stage 1 (`opencode_chat.py`, `opencode_tour.py`) proved the SDK can talk
to a local OpenCode server. Stage 2 proves the same SDK can drive an
OpenCode server that's running inside a remote Daytona sandbox, through
the sandbox's tunneled preview URL.

Why this matters for OmoiOS: the sandbox worker in production will hold
a preview URL + preview-token pair and drive OpenCode over it exactly
this way. This script is the isolated, OmoiOS-free version of that path
so we know the mechanics work before wiring them into the worker.

What the script does:
    1. Spawn a Daytona sandbox from the `omoios-omo-vnc` snapshot
       (ships with Node 25, bun, and `opencode-ai` already installed).
    2. Write `~/.local/share/opencode/auth.json` into the sandbox with
       the zai-coding-plan credential so the in-sandbox OpenCode server
       can actually call a model.
    3. Launch `opencode serve --port 4096 --hostname 0.0.0.0` inside the
       sandbox as a backgrounded session command.
    4. Open the Daytona preview tunnel (`sandbox.get_preview_link(4096)`)
       and poll `<url>/global/health` via `x-daytona-preview-token`
       until it returns 200.
    5. Instantiate `AsyncOpencode(base_url=preview_url, default_headers=
       {"x-daytona-preview-token": token})` and drive a multi-turn
       conversation — the host-side SDK, the in-sandbox server.
    6. Terminate the sandbox on exit.

Env vars:
    DAYTONA_API_KEY               (required)
    OPENCODE_ZAI_KEY              (optional — defaults to the key we use
                                  elsewhere)
    OPENCODE_SANDBOX_SNAPSHOT     (optional — default `omoios-omo-vnc`)

Usage:
    uv run python scripts/opencode_in_sandbox.py
    uv run python scripts/opencode_in_sandbox.py --keep-sandbox
    uv run python scripts/opencode_in_sandbox.py --interactive
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any, Optional

import httpx


DEFAULT_SNAPSHOT = "omoios-omo-vnc"
DEFAULT_PROVIDER = "zai-coding-plan"
DEFAULT_MODEL = "glm-5.1"
DEFAULT_PORT = 4096

# Same key the host-side tour used. Lives in env in real life; hardcoded
# fallback here so `uv run` just works from a fresh checkout.
DEFAULT_ZAI_KEY = "d372fd4ff6aa4e939084c767f7a0333b.EBGBvMQhO3lwN1mR"

SCRIPT_PROMPTS = [
    "Introduce yourself in one short sentence.",
    "Remember the word 'thunderpike'. Acknowledge briefly.",
    "What was the word I asked you to remember?",
    "List three things you can do as a coding agent, one per bullet.",
    "Thanks! Goodbye.",
]


# ─── sandbox lifecycle ───────────────────────────────────────────────────────


def _make_daytona():
    from daytona import Daytona, DaytonaConfig

    api_key = os.environ.get("DAYTONA_API_KEY")
    if not api_key:
        raise RuntimeError("DAYTONA_API_KEY env var is required")
    return Daytona(
        DaytonaConfig(
            api_key=api_key,
            api_url=os.environ.get("DAYTONA_API_URL", "https://app.daytona.io/api"),
            target=os.environ.get("DAYTONA_TARGET", "us"),
        )
    )


def spawn_sandbox(snapshot: str):
    from daytona import CreateSandboxFromSnapshotParams

    d = _make_daytona()
    params = CreateSandboxFromSnapshotParams(
        snapshot=snapshot,
        labels={"purpose": "opencode-stage-2", "ts": str(int(time.time()))},
        env_vars={"OPENCODE_STAGE2": "1"},
    )
    print(f"creating sandbox from snapshot={snapshot} …")
    sb = d.create(params, timeout=120)
    print(f"sandbox id: {sb.id}")
    return sb


def run_cmd(sandbox, cmd: str, *, timeout: int = 30) -> str:
    """Fire a one-shot command in the sandbox and return stdout."""
    result = sandbox.process.exec(cmd, timeout=timeout)
    out = (
        getattr(result, "result", None)
        or getattr(result, "stdout", None)
        or ""
    )
    return str(out).strip()


def write_auth_json(sandbox, *, zai_key: str) -> None:
    """Render auth.json inside the sandbox so OpenCode has creds on boot.

    Daytona sandboxes default to the `daytona` user (home at
    `/home/daytona`), so OpenCode reads from `~/.local/share/opencode/
    auth.json` under that home — not /root.
    """
    auth = {
        "zai-coding-plan": {"type": "api", "key": zai_key},
    }
    # Resolve $HOME on the sandbox side — don't assume /home/daytona.
    data_dir = "$HOME/.local/share/opencode"
    run_cmd(
        sandbox,
        f"mkdir -p {data_dir} && chmod 0700 {data_dir}",
    )
    payload = json.dumps(auth)
    run_cmd(
        sandbox,
        f"cat > {data_dir}/auth.json <<'JSON'\n{payload}\nJSON",
    )
    run_cmd(sandbox, f"chmod 0600 {data_dir}/auth.json")
    got = run_cmd(sandbox, f"cat {data_dir}/auth.json")
    assert '"zai-coding-plan"' in got, f"auth.json didn't land: {got[:200]}"


def start_opencode(sandbox, *, port: int) -> None:
    """Spawn `opencode serve` as a backgrounded session command."""
    from daytona.common.process import SessionExecuteRequest

    sandbox.process.create_session("opencode-serve")
    req = SessionExecuteRequest(
        command=(
            # nohup + setsid so the process survives the session's lifetime.
            # --hostname 0.0.0.0 so the Daytona reverse-proxy can reach it.
            f"nohup opencode serve --port {port} --hostname 0.0.0.0 "
            "> /tmp/opencode-serve.log 2>&1 &"
        ),
        var_async=True,
    )
    sandbox.process.execute_session_command("opencode-serve", req, timeout=10)


def open_preview(sandbox, *, port: int):
    pp = sandbox.get_preview_link(port)
    return pp.url, pp.token


def wait_for_health(
    url: str, *, token: str, timeout_s: float = 60.0
) -> None:
    deadline = time.monotonic() + timeout_s
    headers = {"x-daytona-preview-token": token}
    last_err: Optional[str] = None
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"{url}/global/health", headers=headers, timeout=3.0)
            if r.status_code == 200:
                return
            last_err = f"{r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = type(exc).__name__
        time.sleep(1.5)
    raise RuntimeError(
        f"in-sandbox opencode did not become healthy (last: {last_err})"
    )


# ─── host-side conversation ──────────────────────────────────────────────────


def response_text(resp: Any) -> str:
    parts = getattr(resp, "parts", None) or []
    chunks: list[str] = []
    for p in parts:
        ptype = getattr(p, "type", None) or (
            p.get("type") if isinstance(p, dict) else None
        )
        if ptype != "text":
            continue
        t = getattr(p, "text", None) or (
            p.get("text") if isinstance(p, dict) else None
        )
        if isinstance(t, str) and t:
            chunks.append(t)
    return "\n".join(chunks).strip()


def rule(title: str) -> None:
    print()
    print("═" * 80)
    print(f"  {title}")
    print("═" * 80)


async def run_conversation(
    *,
    preview_url: str,
    preview_token: str,
    provider: str,
    model: str,
    script: Optional[list[str]],
) -> None:
    from opencode_ai import AsyncOpencode

    headers = {"x-daytona-preview-token": preview_token}
    async with AsyncOpencode(
        base_url=preview_url, timeout=180.0, default_headers=headers
    ) as client:
        # Probe — confirm the server inside the sandbox is really the one
        # we're talking to.
        rule("sandboxed opencode: app.providers()")
        try:
            provs = await client.app.providers()
            connected = []
            for p in getattr(provs, "providers", []) or []:
                pid = getattr(p, "id", None) or (
                    p.get("id") if isinstance(p, dict) else None
                )
                if pid:
                    connected.append(pid)
            print(f"connected providers in sandbox: {connected[:10]}")
            if provider not in connected:
                print(
                    f"warning: {provider!r} not in connected list — "
                    "OpenCode may reject the prompt"
                )
        except Exception as exc:  # noqa: BLE001
            print(f"providers probe failed: {exc}")

        rule("sandboxed opencode: session.create()")
        session = await client.session.create(title="stage-2")
        sid = session.id
        print(f"session: {sid}")

        try:
            model_spec = {"provider_id": provider, "model_id": model}
            if script is not None:
                for i, prompt in enumerate(script, start=1):
                    rule(f"TURN {i} — you")
                    print(prompt)
                    started = time.monotonic()
                    resp = await client.session.prompt(
                        id=sid,
                        parts=[{"type": "text", "text": prompt}],
                        model=model_spec,
                    )
                    rule(
                        f"TURN {i} — sandboxed opencode "
                        f"({time.monotonic() - started:.1f}s)"
                    )
                    print(response_text(resp) or "(no text)")
            else:
                print("(type messages; blank line to exit)")
                loop = asyncio.get_running_loop()
                while True:
                    try:
                        text = await loop.run_in_executor(
                            None, lambda: input("you> ")
                        )
                    except (EOFError, KeyboardInterrupt):
                        print()
                        return
                    text = (text or "").strip()
                    if not text:
                        return
                    started = time.monotonic()
                    resp = await client.session.prompt(
                        id=sid,
                        parts=[{"type": "text", "text": text}],
                        model=model_spec,
                    )
                    print(
                        f"sandboxed opencode "
                        f"({time.monotonic() - started:.1f}s)> "
                        f"{response_text(resp) or '(no text)'}"
                    )
        finally:
            try:
                await client.session.delete(id=sid)
            except Exception:  # noqa: BLE001 — cleanup is best-effort
                pass


# ─── entrypoint ──────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        default=os.environ.get("OPENCODE_SANDBOX_SNAPSHOT", DEFAULT_SNAPSHOT),
    )
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument(
        "--keep-sandbox",
        action="store_true",
        help="Skip the sandbox.delete() step on exit (debug convenience)",
    )
    args = parser.parse_args()

    zai_key = os.environ.get("OPENCODE_ZAI_KEY", DEFAULT_ZAI_KEY)

    sb = None
    try:
        sb = spawn_sandbox(args.snapshot)

        rule("writing auth.json into the sandbox")
        write_auth_json(sb, zai_key=zai_key)
        print("auth.json: ok")

        rule(f"starting opencode serve on :{args.port} inside sandbox")
        start_opencode(sb, port=args.port)
        # Give the server a moment to open the port before the proxy probe.
        time.sleep(2)

        rule("opening Daytona preview tunnel")
        url, token = open_preview(sb, port=args.port)
        print(f"preview url:   {url}")
        print(f"preview token: {token[:8]}… (len {len(token)})")

        rule("polling /global/health through the tunnel")
        wait_for_health(url, token=token, timeout_s=60)
        print("in-sandbox opencode is up and reachable")

        asyncio.run(
            run_conversation(
                preview_url=url,
                preview_token=token,
                provider=args.provider,
                model=args.model,
                script=None if args.interactive else SCRIPT_PROMPTS,
            )
        )
        return 0
    finally:
        if sb is not None and not args.keep_sandbox:
            rule("terminating sandbox")
            try:
                sb.delete()
                print("sandbox deleted")
            except Exception as exc:  # noqa: BLE001
                print(f"sandbox delete failed: {exc}")


if __name__ == "__main__":
    sys.exit(main())
