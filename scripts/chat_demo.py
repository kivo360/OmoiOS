#!/usr/bin/env python3
"""Stand up the OmoiOS backend and run a real chat conversation end-to-end.

What this script does, in order:

    1. Boots `uvicorn omoi_os.api.main:app` on 127.0.0.1:18000 as a
       subprocess with the env vars the chat loop needs (Postgres, Redis,
       credential encryption, feature flags, LLM).
    2. Waits until `/openapi.json` responds.
    3. Uses an existing user (or optionally registers one) and mints a
       short-lived JWT with the backend's AUTH_JWT_SECRET_KEY so we
       never need a browser login.
    4. Ensures the user has a workspace (creates one if needed), because
       SDK-direct sessions require one.
    5. Opens the Python SDK's SSE iterator on `/sessions/{id}/events`
       and prints every envelope as it arrives.
    6. Runs either (a) a scripted conversation from --script or
       (b) an interactive REPL (default).
    7. Shuts uvicorn down cleanly on exit.

Run:

    # Interactive REPL
    uv run python scripts/chat_demo.py

    # Scripted conversation (five canned turns)
    uv run python scripts/chat_demo.py --scripted

    # Against an already-running backend (skip the boot step)
    uv run python scripts/chat_demo.py --no-boot

Why a script instead of a notebook: a script is reproducible — same
output every run, one command, nothing to copy-paste. The script
prints timing so you can see that live SSE delivery is actually live.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
SDK_SRC = REPO_ROOT / "sdk" / "python"

# Make the in-tree Python SDK importable without a prior `pip install`.
sys.path.insert(0, str(SDK_SRC))

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18000
DEFAULT_USER_ID = "38348faf-0354-40f8-b161-d770319fd72d"
DEFAULT_USER_EMAIL = "testuser_0d6be1a4@example.com"

DEFAULT_SCRIPT = [
    "hi! remember my name is kevin.",
    "cool. what is 2 + 2?",
    "nice. and what is my name?",
    "what's the capital of france?",
    "thanks, bye.",
]


# ─── helpers ─────────────────────────────────────────────────────────────────


def mint_jwt(*, user_id: str, secret: str, ttl_hours: int = 2) -> str:
    from jose import jwt

    payload = {
        "sub": user_id,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def boot_backend(
    *,
    host: str,
    port: int,
    env_overrides: dict[str, str],
) -> subprocess.Popen[bytes]:
    """Start uvicorn in a subprocess with the chat-ready env."""
    env = {**os.environ, **env_overrides}
    cmd = [
        "uv",
        "run",
        "uvicorn",
        "omoi_os.api.main:app",
        "--host",
        host,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    proc = subprocess.Popen(
        cmd,
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return proc


def wait_until_up(url: str, *, timeout_s: float = 60.0) -> None:
    import httpx

    deadline = time.monotonic() + timeout_s
    last_err: Optional[str] = None
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=1.5)
            if r.status_code == 200:
                return
            last_err = f"{r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = type(exc).__name__
        time.sleep(0.5)
    raise RuntimeError(f"backend did not come up at {url} (last: {last_err})")


async def ensure_org(
    *, base_url: str, jwt: str, name: str = "Chat Demo"
) -> str:
    """Return the caller's first org id, creating one if needed."""
    import httpx

    headers = {"Authorization": f"Bearer {jwt}"}
    slug = f"chat-demo-{uuid.uuid4().hex[:6]}"
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(
            f"{base_url}/api/v1/organizations", headers=headers
        )
        if r.status_code == 200:
            items = r.json()
            if isinstance(items, list) and items:
                return items[0]["id"]
        r = await client.post(
            f"{base_url}/api/v1/organizations",
            headers=headers,
            json={"name": name, "slug": slug},
        )
        if r.status_code in (200, 201):
            return r.json()["id"]
        raise RuntimeError(
            f"could not list or create organization: {r.status_code} {r.text}"
        )


async def ensure_workspace(
    *,
    base_url: str,
    jwt: str,
    name: str = "chat-demo",
    slug: str | None = None,
) -> str:
    """Return the caller's first workspace id, creating one if needed."""
    import httpx

    slug = slug or f"chat-demo-{uuid.uuid4().hex[:8]}"
    headers = {"Authorization": f"Bearer {jwt}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(f"{base_url}/api/v1/workspaces", headers=headers)
        if r.status_code == 200:
            items = r.json()
            if isinstance(items, list) and items:
                return items[0]["id"]
        # Make sure the caller has an org to hang the workspace off.
        org_id = await ensure_org(base_url=base_url, jwt=jwt)
        body = {"name": name, "slug": slug, "organization_id": org_id}
        r = await client.post(
            f"{base_url}/api/v1/workspaces", headers=headers, json=body
        )
        if r.status_code in (200, 201):
            return r.json()["id"]
        raise RuntimeError(
            f"could not list or create workspace: {r.status_code} {r.text}"
        )


# ─── printing ────────────────────────────────────────────────────────────────


def _fmt_actor(actor: str) -> str:
    if actor.startswith("user:"):
        return "you"
    if actor == "agent":
        return "agent"
    return actor or "system"


def print_frame(envelope: dict, *, started: float) -> None:
    elapsed = time.monotonic() - started
    etype = envelope.get("type", "?")
    actor = _fmt_actor(envelope.get("actor", ""))
    data = envelope.get("data") or {}
    text = data.get("text")
    prefix = f"[{elapsed:5.1f}s] {actor:5s} {etype:20s}"
    if text:
        print(f"{prefix}  {text}")
    else:
        # non-message events (session.created, session.started, etc.)
        short = {
            k: v
            for k, v in data.items()
            if k in ("prompt", "workspace_id", "error")
        }
        print(f"{prefix}  {short if short else ''}")


# ─── main flow ───────────────────────────────────────────────────────────────


async def run_chat(
    *,
    base_url: str,
    jwt: str,
    script: list[str] | None,
    timeout_per_turn_s: float = 30.0,
) -> None:
    from omoios import AsyncOmoiOSClient  # type: ignore[import-not-found]

    async with AsyncOmoiOSClient(base_url=base_url, jwt_token=jwt) as client:
        ws_id = await ensure_workspace(base_url=base_url, jwt=jwt)
        print(f"workspace: {ws_id}")

        session = await client.sessions.create(
            workspace_id=ws_id,
            prompt=(script[0] if script else "hi! ready to chat?"),
        )
        session_id = session.id
        print(f"session:   {session_id}")
        print("─" * 80)

        started = time.monotonic()
        stream_task: asyncio.Task[None] | None = None

        # Track agent turns so the scripted flow can wait for the reply
        # before sending the next prompt.
        agent_turn_received = asyncio.Event()

        async def tail_events() -> None:
            async for evt in client.sessions.events(session_id):
                envelope = evt.model_dump() if hasattr(evt, "model_dump") else dict(evt)
                print_frame(envelope, started=started)
                if (
                    envelope.get("type") == "session.message"
                    and envelope.get("actor") == "agent"
                ):
                    agent_turn_received.set()

        stream_task = asyncio.create_task(tail_events())

        try:
            if script:
                # The first prompt was sent at create-time. Skip it here.
                # Wait for the initial agent response before sending turn 2.
                for i, text in enumerate(script):
                    if i == 0:
                        await _await_agent(
                            agent_turn_received, timeout=timeout_per_turn_s
                        )
                        continue
                    print(f"[    ↦] you   sending            {text}")
                    await client.sessions.reply(session_id, text)
                    await _await_agent(
                        agent_turn_received, timeout=timeout_per_turn_s
                    )
            else:
                await interactive_loop(
                    client=client,
                    session_id=session_id,
                    agent_turn_received=agent_turn_received,
                    timeout=timeout_per_turn_s,
                )
        finally:
            if stream_task is not None:
                stream_task.cancel()
                try:
                    await stream_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass


async def _await_agent(event: asyncio.Event, *, timeout: float) -> None:
    try:
        await asyncio.wait_for(event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        print(f"(no agent response within {timeout:.0f}s — continuing)")
    event.clear()


async def interactive_loop(
    *,
    client,
    session_id: str,
    agent_turn_received: asyncio.Event,
    timeout: float,
) -> None:
    print("(type messages and press enter; blank line or Ctrl+D to exit)")
    # Wait for the first agent response to the initial prompt.
    await _await_agent(agent_turn_received, timeout=timeout)

    loop = asyncio.get_running_loop()
    while True:
        try:
            text = await loop.run_in_executor(None, lambda: input("you> "))
        except (EOFError, KeyboardInterrupt):
            print()
            return
        text = (text or "").strip()
        if not text:
            return
        await client.sessions.reply(session_id, text)
        await _await_agent(agent_turn_received, timeout=timeout)


# ─── entrypoint ──────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="End-to-end chat demo")
    parser.add_argument(
        "--no-boot",
        action="store_true",
        help="Don't start uvicorn; assume it's already running on the given port",
    )
    parser.add_argument(
        "--scripted",
        action="store_true",
        help="Run the canned DEFAULT_SCRIPT instead of the interactive REPL",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Backend port (default 18000)"
    )
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="Backend host (default 127.0.0.1)"
    )
    parser.add_argument(
        "--user-id",
        default=DEFAULT_USER_ID,
        help="User id to mint a JWT for (must exist in the DB)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-turn wait for the agent response (seconds)",
    )
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    # Mandatory env. We default to the project's local-dev values so the
    # script runs out of the box on a developer's machine; override via
    # shell env when pointing at a different backend.
    required_env = {
        "DATABASE_URL": os.environ.get(
            "DATABASE_URL", "postgresql+psycopg://kevinhill@localhost:5432/omoi_os_dev"
        ),
        "REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        "CREDENTIAL_ENCRYPTION_KEY": os.environ.get(
            "CREDENTIAL_ENCRYPTION_KEY",
            "ef32fadf66789e3d340b9c5eab396938828988d0ac5d5c925ee1102bf749bdee",
        ),
        "FEATURE_SESSIONS_API_V1": "true",
        "FEATURE_ENVIRONMENTS_V1": "true",
        "FEATURE_BROKER_ENABLED": "true",
        "FEATURE_ARTIFACTS_UNIFIED_V1": "true",
        "FEATURE_WEBHOOKS_ENABLED": "true",
        "LLM_API_KEY": os.environ.get(
            "LLM_API_KEY", "009332196c644810b859e88f26d28fe3.a9dfM8z1qQDWCpiN"
        ),
        "LLM_BASE_URL": os.environ.get(
            "LLM_BASE_URL", "https://api.z.ai/api/coding/paas/v4"
        ),
        "LLM_MODEL": os.environ.get("LLM_MODEL", "glm-4.6"),
    }

    secret = os.environ.get(
        "AUTH_JWT_SECRET_KEY",
        "601a3aad1cd0e00d3fbb9e1dd5b59cf68e388ab70d631d9bea2cac32c698f585",
    )
    jwt = mint_jwt(user_id=args.user_id, secret=secret)

    proc: Optional[subprocess.Popen[bytes]] = None
    try:
        if not args.no_boot:
            print(f"booting backend at {base_url} …")
            proc = boot_backend(
                host=args.host, port=args.port, env_overrides=required_env
            )
            wait_until_up(f"{base_url}/openapi.json", timeout_s=60)
            print("backend is up")
        else:
            wait_until_up(f"{base_url}/openapi.json", timeout_s=5)

        script = DEFAULT_SCRIPT if args.scripted else None
        asyncio.run(
            run_chat(
                base_url=base_url,
                jwt=jwt,
                script=script,
                timeout_per_turn_s=args.timeout,
            )
        )
    finally:
        if proc is not None:
            # The subprocess uses its own session so we can SIGTERM the
            # whole group (uvicorn spawns a reloader + worker).
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
