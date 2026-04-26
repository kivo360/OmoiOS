"""Probe 7b — session.status reaches a terminal value.

Polls `GET /api/v1/sessions/{id}` until `status ∈ {succeeded, failed,
cancelled}` or the budget elapses. This is independent of the SSE
stream — proves the underlying Task's status field transitioned per
the spec §03 contract (commit 903f510a maps Task.status `completed`
→ session.status `succeeded` at the response boundary).

When this FAILs but `chat_responder_fires` PASSed, the bug is in the
status-transition path (e.g. `update_task_status` raised, or the
event_envelope mapping silently dropped).
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from scripts.poof._common import StepResult, save_probe_state
from scripts.poof._settings import get_settings


PROBE_NAME = "session_reaches_terminal"

_TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


async def run(client: Any, state: dict) -> StepResult:
    settings = get_settings()
    t = time.perf_counter()
    sid = state["session_id"]
    deadline = time.time() + settings.timeout_per_step_s

    last_status: str = "?"
    while time.time() < deadline:
        sess = await client.sessions.get(sid)
        last_status = sess.status or "?"
        if last_status in _TERMINAL_STATUSES:
            save_probe_state(
                PROBE_NAME,
                {"session_id": sid, "final_status": last_status},
            )
            ok = last_status == "succeeded"
            return StepResult(
                "PASS" if ok else "FAIL",
                (time.perf_counter() - t) * 1000,
                f"final_status={last_status}",
            )
        await asyncio.sleep(1.0)

    return StepResult(
        "FAIL",
        (time.perf_counter() - t) * 1000,
        f"non-terminal after {settings.timeout_per_step_s}s "
        f"(last={last_status})",
    )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(["session_create", PROBE_NAME])
    async with build_client() as c:
        result = await run(c, state)
    print_step(7, "session.terminal", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
