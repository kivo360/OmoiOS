"""Probe 3 — credential find-or-create.

Ensures the workspace has a Fireworks API-key binding under
`POOF_CREDENTIAL_NAME`. Reuses if present; else creates one with the
key from `FIREWORKS_API_KEY`. Caches `binding_id` for the
env-version-bind-alias probe.
"""

from __future__ import annotations

import time
from typing import Any

from scripts.poof._common import StepResult, save_probe_state
from scripts.poof._settings import get_settings


PROBE_NAME = "credential_find_or_create"


async def run(client: Any, state: dict) -> StepResult:
    from omoios.types import BindingKind, CreateCredentialRequest

    settings = get_settings()
    t = time.perf_counter()
    ws = state["workspace_id"]
    existing = await client.credentials.list(workspace_id=ws)
    found = next(
        (b for b in existing if b.name == settings.credential_name), None
    )
    if found is not None:
        state["binding_id"] = str(found.id)
        save_probe_state(PROBE_NAME, {"binding_id": str(found.id)})
        return StepResult(
            "PASS",
            (time.perf_counter() - t) * 1000,
            f"reused binding={str(found.id)[:8]}…",
        )

    binding = await client.credentials.create(
        CreateCredentialRequest(
            workspace_id=ws,
            kind=BindingKind.BEARER_SECRET,
            name=settings.credential_name,
            value=settings.fireworks_api_key,
        )
    )
    state["binding_id"] = str(binding.id)
    save_probe_state(PROBE_NAME, {"binding_id": str(binding.id)})
    return StepResult(
        "PASS",
        (time.perf_counter() - t) * 1000,
        f"new binding={str(binding.id)[:8]}…",
    )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(
        ["auth_whoami", "workspace_find_or_create", PROBE_NAME]
    )
    async with build_client() as c:
        result = await run(c, state)
    print_step(3, "credential", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
