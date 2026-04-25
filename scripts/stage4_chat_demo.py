#!/usr/bin/env python3
"""Stage 4: chat against OmoiOS with the sandboxed-agent backend wired in.

Boots the OmoiOS backend with `FEATURE_SANDBOXED_AGENT_ENABLED=true`,
opens a chat session via the Python SDK, and holds a multi-turn
conversation. The responder routes each turn through an opencode server
running inside a Daytona sandbox that's spawned on first message and
reused for the rest of the session.

What this proves:
    • The `sandboxed_agent` service spawns one Daytona sandbox per
      OmoiOS session on first message and reuses it for follow-ups.
    • `chat_responder` transparently dispatches the turn through
      opencode-ai when the feature flag is on, and keeps the direct
      LLM fallback when the sandboxed path errors out.
    • The SSE stream on the OmoiOS side sees `session.message` envelopes
      with `actor=agent` arriving live, same shape as stages 2/3.
    • Deleting the OmoiOS session tears the sandbox down.

The first-turn latency will be ~10-20s because of the sandbox spawn.
Subsequent turns are ~model latency only (SDK overhead is ~300ms).

Env:
    DAYTONA_API_KEY         required — sandbox provisioning
    OPENCODE_ZAI_KEY        required — auth.json written into the sandbox
    AUTH_JWT_SECRET_KEY     optional — defaults to the project dev key

Usage:
    uv run python scripts/stage4_chat_demo.py
    uv run python scripts/stage4_chat_demo.py --interactive
    uv run python scripts/stage4_chat_demo.py --no-boot   # backend already running
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

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
SDK_SRC = REPO_ROOT / "sdk" / "python"
sys.path.insert(0, str(SDK_SRC))

DEFAULT_USER_ID = "38348faf-0354-40f8-b161-d770319fd72d"
AUTH_JWT_SECRET_DEFAULT = (
    "601a3aad1cd0e00d3fbb9e1dd5b59cf68e388ab70d631d9bea2cac32c698f585"
)
OMOIOS_URL = "http://127.0.0.1:18000"

SCRIPTED_TURNS = [
    "Hi! Can you introduce yourself in one short sentence?",
    "Create /tmp/stage4-greet.txt containing only the word 'hello'. Use your tools.",
    "Now cat the file back to me and paste the contents verbatim.",
    "Thanks — goodbye.",
]


# ─── helpers ─────────────────────────────────────────────────────────────────


def mint_jwt(user_id: str) -> str:
    from jose import jwt

    secret = os.environ.get("AUTH_JWT_SECRET_KEY", AUTH_JWT_SECRET_DEFAULT)
    payload = {
        "sub": user_id,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=2),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def boot_backend() -> subprocess.Popen[bytes]:
    env = {
        **os.environ,
        "DATABASE_URL": os.environ.get(
            "DATABASE_URL",
            "postgresql+psycopg://kevinhill@localhost:5432/omoi_os_dev",
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
        # The star of the show.
        "FEATURE_SANDBOXED_AGENT_ENABLED": "true",
        # Fallback path for when the sandboxed agent errors — keeps chat
        # from hanging silently.
        "LLM_API_KEY": os.environ.get(
            "LLM_API_KEY", "009332196c644810b859e88f26d28fe3.a9dfM8z1qQDWCpiN"
        ),
        "LLM_BASE_URL": os.environ.get(
            "LLM_BASE_URL", "https://api.z.ai/api/coding/paas/v4"
        ),
        "LLM_MODEL": os.environ.get("LLM_MODEL", "glm-4.6"),
    }
    return subprocess.Popen(
        [
            "uv", "run", "uvicorn",
            "omoi_os.api.main:app",
            "--host", "127.0.0.1",
            "--port", "18000",
            "--log-level", "warning",
        ],
        cwd=str(BACKEND_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )


def wait_until_up(url: str, *, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            r = httpx.get(url, timeout=1.5)
            if r.status_code == 200:
                return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.5)
    raise RuntimeError(f"backend never came up: {url}")


def stop_process(proc: subprocess.Popen[bytes]) -> None:
    for kill in (lambda: os.killpg(proc.pid, signal.SIGTERM), proc.terminate):
        try:
            kill()
            break
        except (ProcessLookupError, PermissionError):
            continue
        except Exception:  # noqa: BLE001
            continue
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()


async def ensure_workspace(jwt: str) -> str:
    headers = {"Authorization": f"Bearer {jwt}"}
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.get(f"{OMOIOS_URL}/api/v1/workspaces", headers=headers)
        if r.status_code == 200:
            items = r.json()
            if items:
                return items[0]["id"]
        r = await c.get(f"{OMOIOS_URL}/api/v1/organizations", headers=headers)
        orgs = r.json() if r.status_code == 200 else []
        if not orgs:
            r = await c.post(
                f"{OMOIOS_URL}/api/v1/organizations",
                headers=headers,
                json={"name": "Stage4", "slug": f"stage4-{uuid.uuid4().hex[:6]}"},
            )
            r.raise_for_status()
            org_id = r.json()["id"]
        else:
            org_id = orgs[0]["id"]
        r = await c.post(
            f"{OMOIOS_URL}/api/v1/workspaces",
            headers=headers,
            json={
                "name": "stage4",
                "slug": f"stage4-{uuid.uuid4().hex[:8]}",
                "organization_id": org_id,
            },
        )
        r.raise_for_status()
        return r.json()["id"]


# ─── chat flow ──────────────────────────────────────────────────────────────


def fmt_actor(actor: str) -> str:
    if actor.startswith("user:"):
        return "you"
    if actor == "agent":
        return "agent"
    return actor or "system"


def rule(title: str) -> None:
    print()
    print("═" * 80)
    print(f"  {title}")
    print("═" * 80)


async def wait_for_agent_after_seq(
    jwt: str, session_id: str, baseline_seq: int, *, timeout_s: float
) -> tuple[int, str]:
    """Poll the events endpoint until a new agent turn with seq > baseline."""
    headers = {"Authorization": f"Bearer {jwt}"}
    deadline = time.monotonic() + timeout_s
    async with httpx.AsyncClient(timeout=15.0) as c:
        while time.monotonic() < deadline:
            r = await c.get(
                f"{OMOIOS_URL}/api/v1/events?task_id={session_id}&limit=500",
                headers=headers,
            )
            if r.status_code == 200:
                for evt in r.json() or []:
                    if evt.get("type") != "session.message":
                        continue
                    if evt.get("actor") != "agent":
                        continue
                    seq = int(evt.get("seq") or 0)
                    if seq <= baseline_seq:
                        continue
                    return seq, (evt.get("data") or {}).get("text", "")
            await asyncio.sleep(0.8)
    return -1, "(no agent response within timeout)"


async def latest_seq(jwt: str, session_id: str) -> int:
    headers = {"Authorization": f"Bearer {jwt}"}
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(
            f"{OMOIOS_URL}/api/v1/events?task_id={session_id}&limit=500",
            headers=headers,
        )
    if r.status_code != 200:
        return 0
    seqs = [int(e.get("seq") or 0) for e in r.json() or []]
    return max(seqs) if seqs else 0


async def run_chat(*, jwt: str, script: Optional[list[str]]) -> None:
    from omoios import AsyncOmoiOSClient  # type: ignore[import-not-found]

    ws_id = await ensure_workspace(jwt)
    print(f"workspace: {ws_id}")

    async with AsyncOmoiOSClient(base_url=OMOIOS_URL, jwt_token=jwt) as client:
        first_turn = (script[0] if script else "hi! ready to chat via sandbox?")
        print(f"creating OmoiOS session (initial prompt → {first_turn!r})")
        session = await client.sessions.create(
            workspace_id=ws_id, prompt=first_turn
        )
        sid = session.id
        print(f"session: {sid}")
        rule("initial turn (sandbox spawn happens here — expect ~10-20s)")

        try:
            # Wait for the initial agent response (responder was kicked
            # off by session.create on the backend side).
            baseline = 0
            started = time.monotonic()
            seq, reply = await wait_for_agent_after_seq(
                jwt, sid, baseline, timeout_s=120.0
            )
            print(f"agent ({time.monotonic() - started:.1f}s)> {reply}")

            if script is not None:
                for i, text in enumerate(script[1:], start=2):
                    rule(f"turn {i}")
                    print(f"you> {text}")
                    baseline = await latest_seq(jwt, sid)
                    await client.sessions.reply(sid, text)
                    started = time.monotonic()
                    seq, reply = await wait_for_agent_after_seq(
                        jwt, sid, baseline, timeout_s=120.0
                    )
                    print(f"agent ({time.monotonic() - started:.1f}s)> {reply}")
            else:
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
                    baseline = await latest_seq(jwt, sid)
                    await client.sessions.reply(sid, text)
                    started = time.monotonic()
                    seq, reply = await wait_for_agent_after_seq(
                        jwt, sid, baseline, timeout_s=120.0
                    )
                    print(f"agent ({time.monotonic() - started:.1f}s)> {reply}")
        finally:
            rule("DELETE session → sandbox is torn down")
            try:
                await client.sessions.cancel(sid)
                print("session cancelled; sandbox cleanup fired on backend")
            except Exception as exc:  # noqa: BLE001
                print(f"cancel failed: {exc}")


# ─── entrypoint ─────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-boot", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()

    if not os.environ.get("DAYTONA_API_KEY"):
        print("ERROR: DAYTONA_API_KEY must be set (sandbox provisioning).")
        return 2

    jwt = mint_jwt(DEFAULT_USER_ID)

    proc: Optional[subprocess.Popen[bytes]] = None
    try:
        if not args.no_boot:
            print("booting OmoiOS backend with FEATURE_SANDBOXED_AGENT_ENABLED=true …")
            proc = boot_backend()
            wait_until_up(f"{OMOIOS_URL}/openapi.json", timeout_s=60)
            print(f"backend up at {OMOIOS_URL}")
        else:
            wait_until_up(f"{OMOIOS_URL}/openapi.json", timeout_s=5)

        asyncio.run(
            run_chat(
                jwt=jwt,
                script=None if args.interactive else SCRIPTED_TURNS,
            )
        )
        return 0
    finally:
        if proc is not None:
            stop_process(proc)


if __name__ == "__main__":
    sys.exit(main())
