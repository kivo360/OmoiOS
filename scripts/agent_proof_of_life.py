#!/usr/bin/env python3
# Agent proof-of-life — step-by-step diagnostic.
#
# Each step is a checkpoint that prints PASS/FAIL within ~10s.
# Resource ids are cached in .poof.state.json so re-runs (and
# `--step N` invocations) reuse what already exists instead of
# recreating it. The first step that fails stops the chain.
#
# Run via the pre-warmed venv (instant) — NOT `uv run` which
# re-resolves on every invocation:
#   .venv/bin/python scripts/agent_proof_of_life.py            # all steps
#   .venv/bin/python scripts/agent_proof_of_life.py --step 3   # just step 3
#   .venv/bin/python scripts/agent_proof_of_life.py --reset    # clear state
#
# Required env (sourced from backend/.env.smoke-test or
# backend/.env.smoke-test.local):
#   OMOIOS_API_BASE_URL
#   OMOIOS_PLATFORM_API_KEY
#   OMOIOS_TEST_WORKSPACE_A   (used as default ws if no cached one)
#   OMOIOS_TEST_ORG_ID
#   FIREWORKS_API_KEY         (must exist in shell env)
#
# DATABASE_URL must point at the same DB the API uses (step 5 does
# a direct write to env_version.credentials).

from __future__ import annotations

# Print BEFORE the heavy imports so the user sees life immediately
# instead of waiting silently for SDK + backend modules to load.
import sys as _sys
import time as _t

_BOOT_T0 = _t.perf_counter()
print("  ▸ poof booting…", flush=True)
_sys.stdout.flush()

import argparse
import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

print(
    f"  ▸ stdlib loaded ({(_t.perf_counter() - _BOOT_T0) * 1000:.0f}ms)",
    flush=True,
)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "sdk" / "python"))
sys.path.insert(0, str(REPO / "backend"))

# Load backend .env.local (DATABASE_URL etc.) so the DB-direct step
# works without forcing the caller to export it.
_env_local = REPO / "backend" / ".env.local"
if _env_local.exists():
    for line in _env_local.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

STATE_PATH = REPO / ".sisyphus" / "poof.state.json"
EVIDENCE_DIR = REPO / ".sisyphus" / "evidence"

# Fixed resource names so re-runs find the same things instead of
# making new ones every time.
POOF_WORKSPACE_NAME = "poof-life"
POOF_CREDENTIAL_NAME = "poof-fireworks-ai"
POOF_ENV_NAME = "poof-kimi"
POOF_ALIAS = "fireworks-ai"


# ─── tiny CLI / output helpers ──────────────────────────────────────────────


class StepResult:
    __slots__ = ("status", "elapsed_ms", "detail")

    def __init__(
        self, status: str, elapsed_ms: float, detail: Optional[str] = None
    ) -> None:
        self.status = status  # "PASS" / "FAIL" / "SKIP"
        self.elapsed_ms = elapsed_ms
        self.detail = detail


def _print_step(num: int, name: str, result: StepResult) -> None:
    glyph = {"PASS": "✓", "FAIL": "✗", "SKIP": "·"}[result.status]
    color = {"PASS": "\033[32m", "FAIL": "\033[31m", "SKIP": "\033[90m"}[
        result.status
    ]
    reset = "\033[0m"
    detail = f"  {result.detail}" if result.detail else ""
    print(
        f"  {color}{glyph} step {num} {name:<14}{reset}"
        f"  {result.status:>4}  {result.elapsed_ms:>5.0f}ms{detail}",
        flush=True,
    )


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except json.JSONDecodeError:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


# ─── step implementations ───────────────────────────────────────────────────


async def step_1_whoami(c: Any, state: dict) -> StepResult:
    t = time.perf_counter()
    r = await c._request("GET", "/api/v1/auth/me")
    body = r.json()
    state["user_id"] = body.get("id") or body.get("user_id")
    state["org_id"] = body.get("organization_id") or os.environ.get(
        "OMOIOS_TEST_ORG_ID"
    )
    return StepResult(
        "PASS",
        (time.perf_counter() - t) * 1000,
        f"user={state.get('user_id', '?')[:8]}…",
    )


async def step_2_workspace(c: Any, state: dict) -> StepResult:
    t = time.perf_counter()
    r = await c._request("GET", "/api/v1/workspaces")
    items = r.json() if isinstance(r.json(), list) else r.json().get("items", [])
    found = next((w for w in items if w.get("name") == POOF_WORKSPACE_NAME), None)
    if found is not None:
        state["workspace_id"] = found["id"]
        return StepResult(
            "PASS",
            (time.perf_counter() - t) * 1000,
            f"reused ws={found['id'][:8]}…",
        )
    # Create new
    r = await c._request(
        "POST",
        "/api/v1/workspaces",
        json={
            "name": POOF_WORKSPACE_NAME,
            "slug": f"poof-{int(time.time())}",
            "org_id": state["org_id"],
        },
    )
    body = r.json()
    state["workspace_id"] = body["id"]
    return StepResult(
        "PASS", (time.perf_counter() - t) * 1000, f"new ws={body['id'][:8]}…"
    )


async def step_3_credential(c: Any, state: dict) -> StepResult:
    from omoios.types import BindingKind, CreateCredentialRequest

    t = time.perf_counter()
    fw = os.environ.get("FIREWORKS_API_KEY")
    if not fw:
        return StepResult("FAIL", 0, "FIREWORKS_API_KEY not set in shell")
    ws = state["workspace_id"]
    existing = await c.credentials.list(workspace_id=ws)
    found = next((b for b in existing if b.name == POOF_CREDENTIAL_NAME), None)
    if found is not None:
        state["binding_id"] = str(found.id)
        return StepResult(
            "PASS",
            (time.perf_counter() - t) * 1000,
            f"reused binding={str(found.id)[:8]}…",
        )
    binding = await c.credentials.create(
        CreateCredentialRequest(
            workspace_id=ws,
            kind=BindingKind.BEARER_SECRET,
            name=POOF_CREDENTIAL_NAME,
            value=fw,
        )
    )
    state["binding_id"] = str(binding.id)
    return StepResult(
        "PASS",
        (time.perf_counter() - t) * 1000,
        f"new binding={str(binding.id)[:8]}…",
    )


async def step_4_environment(c: Any, state: dict) -> StepResult:
    from omoios.types import CreateEnvironmentRequest

    t = time.perf_counter()
    envs = await c.environments.list(state["org_id"])
    found = next((e for e in envs if e.name == POOF_ENV_NAME), None)
    if found is not None:
        state["env_id"] = str(found.id)
        return StepResult(
            "PASS",
            (time.perf_counter() - t) * 1000,
            f"reused env={str(found.id)[:8]}…",
        )
    env = await c.environments.create(
        CreateEnvironmentRequest(name=POOF_ENV_NAME, org_id=state["org_id"])
    )
    state["env_id"] = str(env.id)
    return StepResult(
        "PASS", (time.perf_counter() - t) * 1000, f"new env={str(env.id)[:8]}…"
    )


async def step_5_env_version(c: Any, state: dict) -> StepResult:
    # Direct DB write — public API doesn't expose env_version.credentials yet.
    t = time.perf_counter()
    from omoi_os.config import get_app_settings
    from omoi_os.models.environment import EnvironmentVersion
    from omoi_os.services.database import DatabaseService

    settings = get_app_settings()
    db = DatabaseService(connection_string=settings.database.url)
    env_id = UUID(state["env_id"])

    with db.get_session() as session:
        ev = (
            session.query(EnvironmentVersion)
            .filter(EnvironmentVersion.environment_id == env_id)
            .order_by(EnvironmentVersion.version_number.desc())
            .first()
        )
        if ev is None:
            # Need to mint v1 via the API first (only `variables` route exists).
            from omoios.types import CreateEnvironmentVersionRequest

            ev_resp = await c.environments.create_version(
                env_id, CreateEnvironmentVersionRequest(variables={})
            )
            ev = (
                session.query(EnvironmentVersion)
                .filter(EnvironmentVersion.id == UUID(str(ev_resp.id)))
                .first()
            )
        creds = dict(ev.credentials or {})
        if creds.get(POOF_ALIAS, {}).get("binding_id") == state["binding_id"]:
            state["env_version_id"] = str(ev.id)
            return StepResult(
                "PASS",
                (time.perf_counter() - t) * 1000,
                f"reused ev={str(ev.id)[:8]}… (alias bound)",
            )
        creds[POOF_ALIAS] = {
            "kind": "bearer_secret",
            "binding_id": state["binding_id"],
        }
        ev.credentials = creds
        session.commit()
        state["env_version_id"] = str(ev.id)
        return StepResult(
            "PASS",
            (time.perf_counter() - t) * 1000,
            f"bound alias on ev={str(ev.id)[:8]}…",
        )


async def step_6_session(c: Any, state: dict) -> StepResult:
    t = time.perf_counter()
    session = await c.sessions.create(
        workspace_id=state["workspace_id"],
        environment_id=state["env_id"],
        prompt="Reply with exactly 3 short bullets explaining how OpenCode finds its provider keys.",
        metadata={"source": "poof", "ts": int(time.time())},
    )
    state["session_id"] = session.id
    return StepResult(
        "PASS",
        (time.perf_counter() - t) * 1000,
        f"session={session.id[:8]}… (status={session.status})",
    )


async def step_7_events(c: Any, state: dict) -> StepResult:
    t = time.perf_counter()
    sid = state["session_id"]
    deadline = time.time() + 300
    terminal = {"session.succeeded", "session.failed", "session.cancelled"}
    seen_types: list[str] = []
    agent_msg_count = 0
    last_status = None
    print(f"    streaming events for {sid[:8]}…  (5min budget)")
    async for evt in c.sessions.events(sid):
        seen_types.append(evt.type)
        if evt.type == "session.message" and evt.actor == "agent":
            agent_msg_count += 1
        # Print every event to make progress visible.
        print(
            f"      seq={evt.seq:>3} {evt.type:<28} actor={evt.actor}",
            flush=True,
        )
        if evt.type in terminal:
            last_status = evt.type
            break
        if time.time() > deadline:
            return StepResult(
                "FAIL",
                (time.perf_counter() - t) * 1000,
                f"timeout after 5min, last={seen_types[-1] if seen_types else '?'}",
            )

    # Final state check
    final = await c.sessions.get(sid)
    state.setdefault("evidence", []).append(
        {
            "session_id": sid,
            "final_status": final.status,
            "event_types": seen_types,
            "agent_msg_count": agent_msg_count,
        }
    )
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_DIR / f"poof-{int(time.time())}.json").write_text(
        json.dumps(state["evidence"][-1], indent=2)
    )
    ok = final.status == "succeeded" and agent_msg_count >= 1
    return StepResult(
        "PASS" if ok else "FAIL",
        (time.perf_counter() - t) * 1000,
        f"final={final.status} agent_msgs={agent_msg_count}",
    )


STEPS = [
    (1, "whoami", step_1_whoami),
    (2, "workspace", step_2_workspace),
    (3, "credential", step_3_credential),
    (4, "environment", step_4_environment),
    (5, "env_version", step_5_env_version),
    (6, "session", step_6_session),
    (7, "events", step_7_events),
]


# ─── orchestration ──────────────────────────────────────────────────────────


@asynccontextmanager
async def _client():
    from omoios import AsyncOmoiOSClient

    api = os.environ["OMOIOS_API_BASE_URL"]
    key = os.environ["OMOIOS_PLATFORM_API_KEY"]
    async with AsyncOmoiOSClient(base_url=api, api_key=key, timeout=60.0) as c:
        yield c


async def main(only_step: Optional[int], reset: bool) -> int:
    if reset and STATE_PATH.exists():
        STATE_PATH.unlink()
        print(f"  · cleared {STATE_PATH}")

    state = _load_state()
    state.setdefault("org_id", os.environ.get("OMOIOS_TEST_ORG_ID"))
    state.setdefault(
        "workspace_id", state.get("workspace_id")
    )  # filled by step 2

    # Step 0 — pre-flight (always runs first, no slot in STEPS).
    t = time.perf_counter()
    api = os.environ.get("OMOIOS_API_BASE_URL")
    if not api:
        print("  ✗ step 0 pre-flight: OMOIOS_API_BASE_URL not set")
        return 1
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as h:
            hr = await h.get(f"{api}/health")
        if hr.status_code != 200:
            _print_step(
                0,
                "pre-flight",
                StepResult(
                    "FAIL",
                    (time.perf_counter() - t) * 1000,
                    f"{api}/health → {hr.status_code}",
                ),
            )
            return 1
    except Exception as exc:  # noqa: BLE001
        _print_step(
            0,
            "pre-flight",
            StepResult(
                "FAIL", (time.perf_counter() - t) * 1000, f"unreachable: {exc}"
            ),
        )
        return 1
    _print_step(
        0, "pre-flight", StepResult("PASS", (time.perf_counter() - t) * 1000, api)
    )

    async with _client() as c:
        for num, name, fn in STEPS:
            if only_step is not None and only_step != num:
                _print_step(num, name, StepResult("SKIP", 0, "not requested"))
                continue
            try:
                result = await fn(c, state)
            except Exception as exc:  # noqa: BLE001
                result = StepResult("FAIL", 0, f"{type(exc).__name__}: {exc}")
            _print_step(num, name, result)
            _save_state(state)
            if result.status == "FAIL":
                print(f"\n  stopped at step {num}")
                return 1

    print(f"\n  ✓ all done — state cached in {STATE_PATH}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--step", type=int, help="run only step N (1-7)")
    p.add_argument(
        "--reset", action="store_true", help="clear cached state before running"
    )
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.step, args.reset)))
