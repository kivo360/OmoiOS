"""Probe 0 — API pre-flight.

Hits `/health` on the configured `OMOIOS_API_BASE_URL` and asserts a 200.
Cheapest probe; runs first so subsequent probes don't waste a session
spawn on an unreachable backend.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from scripts.poof._common import StepResult, save_probe_state
from scripts.poof._settings import get_settings


PROBE_NAME = "api_health"


async def run(_client: Any, state: dict) -> StepResult:
    t = time.perf_counter()
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=5.0) as h:
            r = await h.get(f"{settings.api_base_url}/health")
    except Exception as exc:  # noqa: BLE001
        return StepResult(
            "FAIL",
            (time.perf_counter() - t) * 1000,
            f"unreachable: {type(exc).__name__}: {exc}",
        )
    if r.status_code != 200:
        return StepResult(
            "FAIL",
            (time.perf_counter() - t) * 1000,
            f"{settings.api_base_url}/health → {r.status_code}",
        )
    save_probe_state(PROBE_NAME, {"api_base_url": settings.api_base_url})
    return StepResult(
        "PASS", (time.perf_counter() - t) * 1000, settings.api_base_url
    )


async def _solo() -> int:
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state([PROBE_NAME])
    result = await run(None, state)
    print_step(0, "pre-flight", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
