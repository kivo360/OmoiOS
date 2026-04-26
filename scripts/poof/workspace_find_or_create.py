"""Probe 2 — workspace find-or-create.

Looks up `POOF_WORKSPACE_NAME` (default `poof-life`) on the platform.
Reuses if found; else creates one in the configured org. Caches
`workspace_id` for downstream probes.
"""

from __future__ import annotations

import time
from typing import Any

from scripts.poof._common import StepResult, save_probe_state
from scripts.poof._settings import get_settings


PROBE_NAME = "workspace_find_or_create"


async def run(client: Any, state: dict) -> StepResult:
    settings = get_settings()
    t = time.perf_counter()

    r = await client._request("GET", "/api/v1/workspaces")
    body = r.json()
    items = body if isinstance(body, list) else body.get("items", [])
    found = next(
        (w for w in items if w.get("name") == settings.workspace_name),
        None,
    )
    if found is not None:
        state["workspace_id"] = found["id"]
        save_probe_state(PROBE_NAME, {"workspace_id": found["id"]})
        return StepResult(
            "PASS",
            (time.perf_counter() - t) * 1000,
            f"reused ws={found['id'][:8]}…",
        )

    r = await client._request(
        "POST",
        "/api/v1/workspaces",
        json={
            "name": settings.workspace_name,
            "slug": f"poof-{int(time.time())}",
            "org_id": state["org_id"],
        },
    )
    new = r.json()
    state["workspace_id"] = new["id"]
    save_probe_state(PROBE_NAME, {"workspace_id": new["id"]})
    return StepResult(
        "PASS",
        (time.perf_counter() - t) * 1000,
        f"new ws={new['id'][:8]}…",
    )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(["auth_whoami", PROBE_NAME])
    async with build_client() as c:
        result = await run(c, state)
    print_step(2, "workspace", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
