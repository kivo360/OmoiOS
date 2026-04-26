"""Probe 4 — environment find-or-create.

Ensures an Environment named `POOF_ENV_NAME` (default `poof-kimi`)
exists in the active org. Reuses if found; else creates. Caches
`env_id` for the env-version probe.
"""

from __future__ import annotations

import time
from typing import Any

from scripts.poof._common import StepResult, save_probe_state
from scripts.poof._settings import get_settings


PROBE_NAME = "environment_find_or_create"


async def run(client: Any, state: dict) -> StepResult:
    from omoios.types import CreateEnvironmentRequest

    settings = get_settings()
    t = time.perf_counter()

    envs = await client.environments.list(state["org_id"])
    found = next((e for e in envs if e.name == settings.env_name), None)
    if found is not None:
        state["env_id"] = str(found.id)
        save_probe_state(PROBE_NAME, {"env_id": str(found.id)})
        return StepResult(
            "PASS",
            (time.perf_counter() - t) * 1000,
            f"reused env={str(found.id)[:8]}…",
        )

    env = await client.environments.create(
        CreateEnvironmentRequest(name=settings.env_name, org_id=state["org_id"])
    )
    state["env_id"] = str(env.id)
    save_probe_state(PROBE_NAME, {"env_id": str(env.id)})
    return StepResult(
        "PASS",
        (time.perf_counter() - t) * 1000,
        f"new env={str(env.id)[:8]}…",
    )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(["auth_whoami", PROBE_NAME])
    async with build_client() as c:
        result = await run(c, state)
    print_step(4, "environment", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
