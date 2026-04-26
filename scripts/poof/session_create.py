"""Probe 6 — session.create.

Creates a fresh chat session against the cached workspace + environment.
Does NOT find-or-reuse — every poof run wants a fresh session because
session lifecycle is one-shot. Caches `session_id` for the
chat_responder / session_reaches_terminal / events_stream_terminal probes.
"""

from __future__ import annotations

import time
from typing import Any

from scripts.poof._common import StepResult, save_probe_state


PROBE_NAME = "session_create"

_DEFAULT_PROMPT = (
    "Reply with exactly 3 short bullets explaining how OpenCode finds "
    "its provider keys."
)


async def run(client: Any, state: dict) -> StepResult:
    t = time.perf_counter()
    session = await client.sessions.create(
        workspace_id=state["workspace_id"],
        environment_id=state["env_id"],
        prompt=_DEFAULT_PROMPT,
        metadata={"source": "poof", "ts": int(time.time())},
    )
    state["session_id"] = session.id
    save_probe_state(PROBE_NAME, {"session_id": session.id})
    return StepResult(
        "PASS",
        (time.perf_counter() - t) * 1000,
        f"session={session.id[:8]}… (status={session.status})",
    )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(
        [
            "auth_whoami",
            "workspace_find_or_create",
            "environment_find_or_create",
            "env_version_bind_alias",
            PROBE_NAME,
        ]
    )
    async with build_client() as c:
        result = await run(c, state)
    print_step(6, "session", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
