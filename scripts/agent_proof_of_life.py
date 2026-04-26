#!/usr/bin/env python3
# Single-shot end-to-end agent run against Fireworks Kimi K2.5.
#
# Validates the closing-the-loop step: orchestrator picks pending →
# spawns sandbox → agent makes a real LLM call → emits events →
# finishes. See tasks/agent-proof-of-life-plan.md.
#
# Required env vars (source backend/.env.smoke-test, then export
# FIREWORKS_API_KEY before running):
#
#   OMOIOS_API_BASE_URL
#   OMOIOS_PLATFORM_API_KEY
#   OMOIOS_TEST_WORKSPACE_A
#   OMOIOS_TEST_ORG_ID
#   FIREWORKS_API_KEY            (the fw_… key from Railway)
#
# DATABASE_URL is read from backend/.env.local (same DB the API uses)
# because the public env-version API does not yet expose the
# `credentials` map; we set it via a direct DB write.

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from uuid import UUID

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "sdk" / "python"))
sys.path.insert(0, str(REPO / "backend"))

# Load backend .env.local so DatabaseService can find DATABASE_URL —
# the SDK calls don't need it but the credential-binding shim does.
_env_local = REPO / "backend" / ".env.local"
if _env_local.exists():
    for line in _env_local.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from omoios import AsyncOmoiOSClient  # noqa: E402
from omoios.types import (  # noqa: E402
    BindingKind,
    CreateCredentialRequest,
    CreateEnvironmentRequest,
    CreateEnvironmentVersionRequest,
)


def _bind_credential_to_env_version(
    env_version_id: str, alias: str, binding_id: str, kind: str = "bearer_secret"
) -> None:
    # Direct DB write — public API doesn't yet expose env_version.credentials.
    # The model has a JSONB `credentials` column shaped as
    # {alias: {kind, binding_id}}; spawner reads it at sandbox launch
    # (see backend/omoi_os/services/modal_spawner.py:_build_env).
    from omoi_os.config import get_app_settings
    from omoi_os.models.environment import EnvironmentVersion
    from omoi_os.services.database import DatabaseService

    settings = get_app_settings()
    db = DatabaseService(connection_string=settings.database.url)

    with db.get_session() as session:
        ev = (
            session.query(EnvironmentVersion)
            .filter(EnvironmentVersion.id == UUID(env_version_id))
            .first()
        )
        if ev is None:
            raise RuntimeError(f"env_version {env_version_id} not found")
        creds = dict(ev.credentials or {})
        creds[alias] = {"kind": kind, "binding_id": binding_id}
        ev.credentials = creds
        session.commit()


async def main() -> int:
    api = os.environ["OMOIOS_API_BASE_URL"]
    key = os.environ["OMOIOS_PLATFORM_API_KEY"]
    ws = os.environ["OMOIOS_TEST_WORKSPACE_A"]
    org = os.environ["OMOIOS_TEST_ORG_ID"]
    fw = os.environ.get("FIREWORKS_API_KEY")
    if not fw:
        print("ERROR: FIREWORKS_API_KEY not set in shell")
        print("       export FIREWORKS_API_KEY=fw_… (the Railway value)")
        return 1

    started = time.time()
    ts = int(started)

    async with AsyncOmoiOSClient(base_url=api, api_key=key, timeout=60.0) as c:
        # 1. Bind Fireworks key as a workspace credential.
        binding = await c.credentials.create(
            CreateCredentialRequest(
                workspace_id=ws,
                kind=BindingKind.BEARER_SECRET,
                name=f"fireworks-poc-{ts}",
                value=fw,
            )
        )
        print(f"  ✓ binding {str(binding.id)[:8]}…")

        # 2. Create env + first version (variables empty — broker handles creds).
        env = await c.environments.create(
            CreateEnvironmentRequest(name=f"kimi-poc-{ts}", org_id=org)
        )
        print(f"  ✓ env {str(env.id)[:8]}…")

        env_version = await c.environments.create_version(
            env.id, CreateEnvironmentVersionRequest(variables={})
        )
        print(f"  ✓ env_version {str(env_version.id)[:8]}…")

        # 3. DB-direct credential alias bind.
        _bind_credential_to_env_version(
            str(env_version.id), "fireworks-ai", str(binding.id)
        )
        print("  ✓ bound 'fireworks-ai' alias on env_version")

        # 4. Spawn the session.
        session = await c.sessions.create(
            workspace_id=ws,
            environment_id=str(env.id),
            prompt="Explain in 3 bullets how OpenCode finds its provider keys.",
            metadata={"source": "proof-of-life", "ts": ts},
        )
        print(f"  ✓ session {session.id[:8]}…")

        # 5. Stream events until terminal.
        deadline = time.time() + 300  # 5 min budget
        terminal = {"session.succeeded", "session.failed", "session.cancelled"}
        seen_types: list[str] = []
        agent_message_count = 0
        async for evt in c.sessions.events(session.id):
            seen_types.append(evt.type)
            print(f"    seq={evt.seq:>3} {evt.type:<28} actor={evt.actor}")
            if evt.type == "session.message" and evt.actor == "agent":
                agent_message_count += 1
            if evt.type in terminal:
                print(f"\nTERMINAL: {evt.type}")
                break
            if time.time() > deadline:
                print("\nTIMEOUT after 5min")
                break

        # 6. Final shape check.
        final = await c.sessions.get(session.id)
        print(f"\nfinal_status={final.status}")
        artifacts = await c.sessions.artifacts(session.id)
        print(f"artifacts={len(artifacts)}")
        for a in artifacts[:3]:
            print(f"  • {a.name} ({a.size_bytes}B)")

        # 7. Persist evidence.
        evidence_path = (
            REPO / ".sisyphus" / "evidence" / f"agent-proof-of-life-{ts}.json"
        )
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(
                {
                    "session_id": session.id,
                    "env_id": str(env.id),
                    "env_version_id": str(env_version.id),
                    "binding_id": str(binding.id),
                    "final_status": final.status,
                    "event_types": seen_types,
                    "agent_message_count": agent_message_count,
                    "artifact_count": len(artifacts),
                    "wall_clock_seconds": round(time.time() - started, 1),
                },
                indent=2,
            )
        )
        print(f"\n  ✓ evidence: {evidence_path}")

        ok = (
            final.status == "succeeded"
            and agent_message_count >= 1
            and (time.time() - started) < 300
        )
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
