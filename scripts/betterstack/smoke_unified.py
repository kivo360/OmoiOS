#!/usr/bin/env python3
"""End-to-end smoke test for the unified observability pipeline.

Exercises every signal that ``omoi_os.observability.betterstack`` is
expected to handle, prints PASS/FAIL per signal, and exits non-zero if
anything failed.

Each step is independent so this can be re-run in place — supports
``--step N`` to run a single signal in isolation.

Usage:
    # All signals (uses env vars from your shell or backend/.env)
    uv run python -m scripts.betterstack.smoke_unified

    # Just the trace path
    uv run python -m scripts.betterstack.smoke_unified --step 3

Environment variables read:
    BETTERSTACK_ERRORS_DSN
    BETTERSTACK_SOURCE_TOKEN
    BETTERSTACK_INGESTING_HOST
    BETTERSTACK_HEARTBEAT_TOKEN  (optional)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from typing import Callable

# Add backend/ to path so we can import omoi_os without `uv sync`-ing as
# the cwd package.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO_ROOT, "backend"))


def _step(name: str, fn: Callable[[], bool]) -> bool:
    print(f"  → {name} ... ", end="", flush=True)
    try:
        ok = fn()
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL ({exc})")
        return False
    print("PASS" if ok else "FAIL")
    return ok


def step_init(_unused: object = None) -> bool:
    from omoi_os.observability.betterstack import init_betterstack
    from omoi_os.config import get_app_settings

    s = get_app_settings().betterstack
    if not s.is_otlp_configured and not s.is_errors_configured:
        print("\n    (no BetterStack creds configured; aborting)")
        return False

    handle = init_betterstack(start_heartbeat=False)
    return handle.tracer_provider is not None or handle.sentry_initialized


def step_error() -> bool:
    import sentry_sdk

    try:
        raise RuntimeError("smoke_unified: synthetic error")
    except RuntimeError:
        eid = sentry_sdk.capture_exception()
    sentry_sdk.flush(timeout=5)
    return bool(eid)


def step_trace() -> bool:
    from opentelemetry import trace

    tracer = trace.get_tracer("smoke_unified")
    with tracer.start_as_current_span("smoke-root") as span:
        span.set_attribute("smoke.kind", "trace")
        with tracer.start_as_current_span("smoke-child") as child:
            child.set_attribute("smoke.depth", 1)
            time.sleep(0.05)
    # Force-flush so the trace ships before the script exits.
    from omoi_os.observability.betterstack import get_handle

    h = get_handle()
    if h:
        h.flush()
    return True


def step_metric() -> bool:
    from opentelemetry import metrics

    meter = metrics.get_meter("smoke_unified")
    counter = meter.create_counter("smoke_events_total")
    histogram = meter.create_histogram("smoke_duration_ms", unit="ms")
    counter.add(1, {"kind": "smoke"})
    for v in (1.2, 3.4, 5.6):
        histogram.record(v, {"kind": "smoke"})

    from omoi_os.observability.betterstack import get_handle

    h = get_handle()
    if h:
        h.flush()
    return True


def step_log() -> bool:
    import logging

    logger = logging.getLogger("smoke_unified")
    logger.setLevel(logging.INFO)
    logger.info("smoke_unified: synthetic info log")
    logger.warning("smoke_unified: synthetic warning log")

    from omoi_os.observability.betterstack import get_handle

    h = get_handle()
    if h:
        h.flush()
    return True


async def step_heartbeat_async() -> bool:
    from omoi_os.config import get_app_settings

    s = get_app_settings().betterstack
    if not s.heartbeat_token:
        print("\n    (BETTERSTACK_HEARTBEAT_TOKEN not set; skipping)")
        return True

    import httpx

    url = f"https://uptime.betterstack.com/api/v1/heartbeat/{s.heartbeat_token}"
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(url)
    return resp.status_code < 400


def step_heartbeat() -> bool:
    return asyncio.run(step_heartbeat_async())


STEPS = [
    ("1. Init pipelines", step_init),
    ("2. Error capture (Sentry → BetterStack Errors)", step_error),
    ("3. Trace span (OTLP → BetterStack Telemetry)", step_trace),
    ("4. Metrics (OTLP → BetterStack Telemetry)", step_metric),
    ("5. Logs (OTLP → BetterStack Telemetry)", step_log),
    ("6. Heartbeat (REST → BetterStack Uptime)", step_heartbeat),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--step",
        type=int,
        help="Run only step N (1-based). Step 1 is always run as a prerequisite.",
    )
    args = parser.parse_args()

    print("BetterStack unified smoke test")
    print("=" * 70)

    # Step 1 is always run because it's required by everything else.
    ok = _step(STEPS[0][0], STEPS[0][1])
    if not ok:
        return 1

    failures = 0
    for i, (name, fn) in enumerate(STEPS[1:], start=2):
        if args.step and args.step != i:
            continue
        if not _step(name, fn):
            failures += 1

    print("=" * 70)
    if failures:
        print(f"{failures} signal(s) FAILED")
        return 1
    print("all signals PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
