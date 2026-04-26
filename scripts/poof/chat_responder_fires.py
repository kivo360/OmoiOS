"""Probe 7a — chat_responder fires.

Streams the session events looking for ONE `session.message` event with
`actor=agent`. Budget is `POOF_CHAT_RESPONDER_BUDGET_S` (default 90s).
This proves the chat_responder background task picked up the session
and called the LLM successfully — independent of whether the session
later transitions to a terminal state.

When this probe FAILs, the bug is one of: chat_responder didn't fire,
the LLM call failed, or the agent reply was empty. None of those are
distinguishable from "session never reached terminal" without this
finer-grained check.
"""

from __future__ import annotations

import time
from typing import Any

from scripts.poof._common import StepResult, save_probe_state
from scripts.poof._settings import get_settings


PROBE_NAME = "chat_responder_fires"


async def run(client: Any, state: dict) -> StepResult:
    settings = get_settings()
    t = time.perf_counter()
    sid = state["session_id"]
    deadline = time.time() + settings.chat_responder_budget_s

    seen_types: list[str] = []
    async for evt in client.sessions.events(sid):
        seen_types.append(evt.type)
        if evt.type == "session.message" and evt.actor == "agent":
            save_probe_state(
                PROBE_NAME,
                {
                    "session_id": sid,
                    "agent_message_seq": evt.seq,
                    "event_types_seen": seen_types,
                },
            )
            return StepResult(
                "PASS",
                (time.perf_counter() - t) * 1000,
                f"agent message at seq={evt.seq}",
            )
        if time.time() > deadline:
            return StepResult(
                "FAIL",
                (time.perf_counter() - t) * 1000,
                f"no agent message after {settings.chat_responder_budget_s}s "
                f"(seen={seen_types})",
            )
    return StepResult(
        "FAIL",
        (time.perf_counter() - t) * 1000,
        f"event stream closed without an agent message (seen={seen_types})",
    )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(["session_create", PROBE_NAME])
    async with build_client() as c:
        result = await run(c, state)
    print_step(7, "chat_responder", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
