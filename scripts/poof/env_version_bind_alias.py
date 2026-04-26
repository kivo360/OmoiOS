"""Probe 5 — env_version: bind alias to credential binding.

Creates v1 of the environment if needed, then writes
`credentials[POOF_ALIAS] = {kind: bearer_secret, binding_id}` directly
to the DB (the public API doesn't expose `env_version.credentials`
write yet — only the `variables` route exists).

Caches `env_version_id`.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from scripts.poof._common import StepResult, save_probe_state
from scripts.poof._settings import get_settings


PROBE_NAME = "env_version_bind_alias"


async def run(client: Any, state: dict) -> StepResult:
    from omoi_os.config import get_app_settings
    from omoi_os.models.environment import EnvironmentVersion
    from omoi_os.services.database import DatabaseService

    settings = get_settings()
    t = time.perf_counter()

    backend_settings = get_app_settings()
    db = DatabaseService(connection_string=backend_settings.database.url)
    env_id = UUID(state["env_id"])

    with db.get_session() as session:
        ev = (
            session.query(EnvironmentVersion)
            .filter(EnvironmentVersion.environment_id == env_id)
            .order_by(EnvironmentVersion.version_number.desc())
            .first()
        )
        if ev is None:
            from omoios.types import CreateEnvironmentVersionRequest

            ev_resp = await client.environments.create_version(
                env_id, CreateEnvironmentVersionRequest(variables={})
            )
            ev = (
                session.query(EnvironmentVersion)
                .filter(EnvironmentVersion.id == UUID(str(ev_resp.id)))
                .first()
            )

        creds = dict(ev.credentials or {})
        already_bound = (
            creds.get(settings.alias, {}).get("binding_id") == state["binding_id"]
        )
        if already_bound:
            state["env_version_id"] = str(ev.id)
            save_probe_state(PROBE_NAME, {"env_version_id": str(ev.id)})
            return StepResult(
                "PASS",
                (time.perf_counter() - t) * 1000,
                f"reused ev={str(ev.id)[:8]}… (alias bound)",
            )

        creds[settings.alias] = {
            "kind": "bearer_secret",
            "binding_id": state["binding_id"],
        }
        ev.credentials = creds
        session.commit()
        state["env_version_id"] = str(ev.id)
        save_probe_state(PROBE_NAME, {"env_version_id": str(ev.id)})
        return StepResult(
            "PASS",
            (time.perf_counter() - t) * 1000,
            f"bound alias on ev={str(ev.id)[:8]}…",
        )


async def _solo() -> int:
    from scripts.poof._client import build_client
    from scripts.poof._common import load_merged_state, print_step

    state = load_merged_state(
        [
            "auth_whoami",
            "credential_find_or_create",
            "environment_find_or_create",
            PROBE_NAME,
        ]
    )
    async with build_client() as c:
        result = await run(c, state)
    print_step(5, "env_version", result)
    return 0 if result.status == "PASS" else 1


if __name__ == "__main__":
    import asyncio
    import sys

    sys.exit(asyncio.run(_solo()))
