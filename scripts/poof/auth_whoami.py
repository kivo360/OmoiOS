"""Probe 1 — whoami.

Hits `GET /api/v1/auth/me`, captures `user_id` + `org_id` into shared
state. Confirms the platform API key is valid and which org/user it's
acting as.
"""

from __future__ import annotations

import time
from typing import Any

from scripts.poof._common import StepResult, save_probe_state
from scripts.poof._settings import get_settings


PROBE_NAME = "auth_whoami"


async def run(client: Any, state: dict) -> StepResult:
    t = time.perf_counter()
    r = await client._request("GET", "/api/v1/auth/me")
    body = r.json()
    user_id = body.get("id") or body.get("user_id")
    settings = get_settings()
    org_id = body.get("organization_id") or settings.test_org_id
    state["user_id"] = user_id
    state["org_id"] = org_id
    save_probe_state(PROBE_NAME, {"user_id": user_id, "org_id": org_id})
    return StepResult(
        "PASS",
        (time.perf_counter() - t) * 1000,
        f"user={(user_id or '?')[:8]}…",
    )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(["api_health", PROBE_NAME])
    async with build_client() as c:
        result = await run(c, state)
    print_step(1, "whoami", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
