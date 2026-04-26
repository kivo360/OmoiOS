"""Probe 7c — SSE stream actually delivers the terminal envelope.

Subscribes to `/api/v1/sessions/{id}/events` and asserts that one of
`session.succeeded`, `session.failed`, or `session.cancelled` arrives
before the budget elapses. Distinct from `session_reaches_terminal`
(which polls the GET endpoint) — this probe proves the SSE delivery
path itself is healthy: clients that hang off the event stream actually
see the terminal envelope.

Also writes `.sisyphus/evidence/poof-<ts>.json` with the full event-type
trace + agent_msg_count, mirroring the success-criteria evidence the
monolith captured.
"""

from __future__ import annotations

import json
import time
from typing import Any

from scripts.poof._common import (
    EVIDENCE_DIR,
    StepResult,
    save_probe_state,
)
from scripts.poof._settings import get_settings


PROBE_NAME = "events_stream_terminal"

_TERMINAL = {"session.succeeded", "session.failed", "session.cancelled"}


async def run(client: Any, state: dict) -> StepResult:
    settings = get_settings()
    t = time.perf_counter()
    sid = state["session_id"]
    deadline = time.time() + settings.timeout_per_step_s

    seen_types: list[str] = []
    agent_msg_count = 0
    last_status: str | None = None

    async for evt in client.sessions.events(sid):
        seen_types.append(evt.type)
        if evt.type == "session.message" and evt.actor == "agent":
            agent_msg_count += 1
        if evt.type in _TERMINAL:
            last_status = evt.type
            break
        if time.time() > deadline:
            return StepResult(
                "FAIL",
                (time.perf_counter() - t) * 1000,
                f"timeout after {settings.timeout_per_step_s}s "
                f"(last={seen_types[-1] if seen_types else '?'})",
            )

    if last_status is None:
        return StepResult(
            "FAIL",
            (time.perf_counter() - t) * 1000,
            f"stream closed without terminal (seen={seen_types})",
        )

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    evidence = {
        "session_id": sid,
        "terminal_event": last_status,
        "event_types": seen_types,
        "agent_msg_count": agent_msg_count,
    }
    (EVIDENCE_DIR / f"poof-{int(time.time())}.json").write_text(
        json.dumps(evidence, indent=2)
    )
    save_probe_state(PROBE_NAME, evidence)

    ok = last_status == "session.succeeded" and agent_msg_count >= 1
    return StepResult(
        "PASS" if ok else "FAIL",
        (time.perf_counter() - t) * 1000,
        f"terminal={last_status} agent_msgs={agent_msg_count}",
    )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(["session_create", PROBE_NAME])
    async with build_client() as c:
        result = await run(c, state)
    print_step(7, "events.stream", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
