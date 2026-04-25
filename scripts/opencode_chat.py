#!/usr/bin/env python3
"""Drive an OpenCode server using the official `opencode-ai` SDK.

Stage 1 of the agent-runtime adaptation: prove we can use a non-Claude
agent as a black-box HTTP service through its typed Python SDK.

Why the SDK and not raw httpx: later stages embed OpenCode inside the
OmoiOS sandbox as the agent runtime. When that happens the sandbox
worker will hold an `AsyncOpencode` client pointed at `127.0.0.1:4096`
inside the sandbox and drive it turn-by-turn. Getting the SDK surface
right now — sessions, prompts, streaming, cleanup — means the sandbox
wiring is mechanical later.

What this script does:
    1. Boots `opencode serve` on 127.0.0.1:4096 (skipped with --no-boot).
    2. Instantiates `AsyncOpencode(base_url=...)`.
    3. Confirms the chosen provider is connected via `client.app.providers()`.
    4. Creates a session via `client.session.create()`.
    5. Runs either a 5-turn canned conversation (default) or an
       interactive REPL (--interactive), calling `client.session.prompt(...)`
       for each turn and concatenating the returned `text` parts.
    6. Cleans up the session + subprocess on exit.

SDK: https://github.com/anomalyco/opencode-sdk-python (branch `next`,
PyPI: opencode-ai).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
from typing import Optional

import httpx


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4096
DEFAULT_PROVIDER = "zai-coding-plan"
DEFAULT_MODEL = "glm-5.1"

DEFAULT_SCRIPT = [
    "Hi! I'm testing our integration. Please introduce yourself in one short sentence.",
    "Great. Remember this for later: my favorite number is 17. What's 17 + 5?",
    "What was the number I told you to remember?",
    "Summarize our conversation so far in bullet points, no more than 4 bullets.",
    "Thanks! Goodbye.",
]


# ─── process management ─────────────────────────────────────────────────────


def boot_opencode(*, host: str, port: int) -> subprocess.Popen[bytes]:
    cmd = ["opencode", "serve", "--port", str(port), "--hostname", host]
    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def wait_until_up(base_url: str, *, timeout_s: float = 30.0) -> None:
    deadline = time.monotonic() + timeout_s
    url = f"{base_url}/global/health"
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=1.5)
            if r.status_code == 200:
                return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.5)
    raise RuntimeError(f"opencode did not come up at {url}")


def stop_process(proc: subprocess.Popen[bytes]) -> None:
    """Best-effort cleanup. Tolerates forked children and pgroup perm errors."""
    for kill in (
        lambda: os.killpg(proc.pid, signal.SIGTERM),
        proc.terminate,
    ):
        try:
            kill()
            break
        except (ProcessLookupError, PermissionError):
            continue
        except Exception:  # noqa: BLE001
            continue
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass


# ─── SDK driver ─────────────────────────────────────────────────────────────


def _response_text(resp) -> str:
    """Collect user-facing `text` parts from a SessionPromptResponse.

    The SDK returns Pydantic models with a `parts` list where each part
    is one of: step-start, reasoning, text, tool, file, … We only want
    `text` — reasoning is internal chain-of-thought, step-start is
    orchestration metadata.
    """
    parts = getattr(resp, "parts", None) or []
    chunks: list[str] = []
    for p in parts:
        ptype = getattr(p, "type", None) or (p.get("type") if isinstance(p, dict) else None)
        if ptype != "text":
            continue
        t = getattr(p, "text", None) or (p.get("text") if isinstance(p, dict) else None)
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
    base_url: str,
    provider: str,
    model: str,
    script: Optional[list[str]],
) -> None:
    from opencode_ai import AsyncOpencode

    async with AsyncOpencode(base_url=base_url, timeout=180.0) as client:
        # Sanity check the provider before we send prompts — OpenCode
        # silently returns an unhelpful error if you pick a provider it
        # has no creds configured for.
        try:
            provs = await client.app.providers()
            connected = []
            for p in getattr(provs, "providers", []) or []:
                pid = getattr(p, "id", None) or (
                    p.get("id") if isinstance(p, dict) else None
                )
                if pid:
                    connected.append(pid)
            if connected and provider not in connected:
                print(
                    f"warning: provider {provider!r} not in OpenCode's connected "
                    f"list — first few: {connected[:6]}"
                )
        except Exception as exc:  # noqa: BLE001 — probe is best-effort
            print(f"provider probe skipped: {exc}")

        session = await client.session.create()
        session_id = session.id
        print(f"opencode session: {session_id}")
        print(f"provider/model:   {provider} / {model}")

        try:
            if script is not None:
                for i, prompt in enumerate(script, start=1):
                    rule(f"TURN {i} — you")
                    print(prompt)
                    started = time.monotonic()
                    resp = await client.session.prompt(
                        id=session_id,
                        parts=[{"type": "text", "text": prompt}],
                        model={"provider_id": provider, "model_id": model},
                    )
                    elapsed = time.monotonic() - started
                    rule(f"TURN {i} — opencode ({elapsed:.1f}s)")
                    print(_response_text(resp) or "(no text response)")
            else:
                print("(type messages and press enter; blank line or Ctrl+D to exit)")
                loop = asyncio.get_running_loop()
                while True:
                    try:
                        text = await loop.run_in_executor(
                            None, lambda: input("you> ")
                        )
                    except (EOFError, KeyboardInterrupt):
                        print()
                        break
                    text = (text or "").strip()
                    if not text:
                        break
                    started = time.monotonic()
                    resp = await client.session.prompt(
                        id=session_id,
                        parts=[{"type": "text", "text": text}],
                        model={"provider_id": provider, "model_id": model},
                    )
                    elapsed = time.monotonic() - started
                    print(
                        f"opencode ({elapsed:.1f}s)> "
                        f"{_response_text(resp) or '(no text)'}"
                    )
        finally:
            try:
                await client.session.delete(session_id)
            except Exception:  # noqa: BLE001 — cleanup is best-effort
                pass


# ─── entrypoint ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--no-boot", action="store_true")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="REPL instead of the default scripted conversation",
    )
    args = parser.parse_args()
    base_url = f"http://{args.host}:{args.port}"

    proc: Optional[subprocess.Popen[bytes]] = None
    try:
        if not args.no_boot:
            print("booting OpenCode server …")
            proc = boot_opencode(host=args.host, port=args.port)
            wait_until_up(base_url, timeout_s=30)
            print(f"OpenCode up at {base_url}")
        else:
            wait_until_up(base_url, timeout_s=5)

        asyncio.run(
            run_conversation(
                base_url=base_url,
                provider=args.provider,
                model=args.model,
                script=None if args.interactive else DEFAULT_SCRIPT,
            )
        )
        return 0
    finally:
        if proc is not None:
            stop_process(proc)


if __name__ == "__main__":
    sys.exit(main())
