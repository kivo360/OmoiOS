#!/usr/bin/env python3
# Agent proof-of-life — thin harness around `scripts/poof/` probes.
#
# Each probe lives in its own file under scripts/poof/ and is runnable
# solo for surgical debugging:
#
#   POOF_ENV=local .venv/bin/python -m scripts.poof.chat_responder_fires
#
# This harness:
#   - Loads PoofSettings (`scripts.poof._settings`) once.
#   - Runs the probes in priors-first order; first FAIL stops the chain.
#   - Saves per-probe state under `.sisyphus/poof-state/<probe>.json`
#     (each probe persists itself; this orchestrator just merges them
#     into the shared `state` dict between calls).
#
# Usage:
#   .venv/bin/python scripts/agent_proof_of_life.py            # all probes
#   .venv/bin/python scripts/agent_proof_of_life.py --step 7   # only step 7
#   .venv/bin/python scripts/agent_proof_of_life.py --reset    # clear caches
#
# See `memory/project_poof_settings_and_decomposition.md` for the design
# rationale; `docs/poof-cheatsheet.md` for the tmux + just recipe surface.

from __future__ import annotations

# Print BEFORE the heavy imports so the user sees life immediately.
import sys as _sys
import time as _t

_BOOT_T0 = _t.perf_counter()
print("  ▸ poof booting…", flush=True)
_sys.stdout.flush()

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

print(
    f"  ▸ stdlib loaded ({(_t.perf_counter() - _BOOT_T0) * 1000:.0f}ms)",
    flush=True,
)

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "sdk" / "python"))
sys.path.insert(0, str(REPO / "backend"))
sys.path.insert(0, str(REPO))

from scripts.poof._client import build_client
from scripts.poof._common import (
    StepResult,
    clear_all_probe_state,
    load_merged_state,
    print_step,
)
from scripts.poof import (
    api_health,
    auth_whoami,
    chat_responder_fires,
    credential_find_or_create,
    env_version_bind_alias,
    environment_find_or_create,
    events_stream_terminal,
    session_create,
    session_reaches_terminal,
    workspace_find_or_create,
)


ProbeRun = Callable[[Any, dict], Awaitable[StepResult]]

# (step_number, label, probe_module_name, run_fn, needs_client)
# Step 0 (api_health) doesn't need the AsyncOmoiOSClient — it just hits /health.
PROBES: list[tuple[int, str, str, ProbeRun, bool]] = [
    (0, "pre-flight", api_health.PROBE_NAME, api_health.run, False),
    (1, "whoami", auth_whoami.PROBE_NAME, auth_whoami.run, True),
    (
        2,
        "workspace",
        workspace_find_or_create.PROBE_NAME,
        workspace_find_or_create.run,
        True,
    ),
    (
        3,
        "credential",
        credential_find_or_create.PROBE_NAME,
        credential_find_or_create.run,
        True,
    ),
    (
        4,
        "environment",
        environment_find_or_create.PROBE_NAME,
        environment_find_or_create.run,
        True,
    ),
    (
        5,
        "env_version",
        env_version_bind_alias.PROBE_NAME,
        env_version_bind_alias.run,
        True,
    ),
    (6, "session", session_create.PROBE_NAME, session_create.run, True),
    (
        7,
        "chat_responder",
        chat_responder_fires.PROBE_NAME,
        chat_responder_fires.run,
        True,
    ),
    (
        7,
        "session.terminal",
        session_reaches_terminal.PROBE_NAME,
        session_reaches_terminal.run,
        True,
    ),
    (
        7,
        "events.stream",
        events_stream_terminal.PROBE_NAME,
        events_stream_terminal.run,
        True,
    ),
]


async def main(only_step: Optional[int], reset: bool) -> int:
    if reset:
        clear_all_probe_state()
        print("  · cleared per-probe state caches")

    probe_names = [p[2] for p in PROBES]
    state = load_merged_state(probe_names)

    # Probe 0 doesn't need the client; run it standalone to fail fast on
    # an unreachable backend before we open a session.
    pre_step = PROBES[0]
    pre_result = await _run_one(pre_step, None, state, only_step)
    if pre_result.status == "FAIL":
        print(f"\n  stopped at step {pre_step[0]}")
        return 1

    async with build_client() as client:
        for probe in PROBES[1:]:
            result = await _run_one(probe, client, state, only_step)
            if result.status == "FAIL":
                print(f"\n  stopped at step {probe[0]}")
                return 1

    print(
        "\n  ✓ all done — per-probe state cached in "
        f"{REPO / '.sisyphus' / 'poof-state'}/"
    )
    return 0


async def _run_one(
    probe: tuple[int, str, str, ProbeRun, bool],
    client: Any,
    state: dict,
    only_step: Optional[int],
) -> StepResult:
    step_num, label, _name, run_fn, _needs_client = probe
    if only_step is not None and only_step != step_num:
        result = StepResult("SKIP", 0.0, "not requested")
        print_step(step_num, label, result)
        return result
    try:
        result = await run_fn(client, state)
    except Exception as exc:  # noqa: BLE001
        result = StepResult("FAIL", 0.0, f"{type(exc).__name__}: {exc}")
    print_step(step_num, label, result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--step", type=int, help="run only step N (0-7)")
    p.add_argument(
        "--reset", action="store_true", help="clear cached state before running"
    )
    args = p.parse_args()
    sys.exit(asyncio.run(main(args.step, args.reset)))
