"""Daytona-backed sandbox provider wrapping DaytonaSpawnerService."""

from __future__ import annotations
from typing import Optional
from omoi_os.services.sandbox_provider import SandboxResult, SandboxStatus


class DaytonaProvider:
    """SandboxProvider backed by Daytona Cloud."""

    def __init__(self, spawner):
        self._spawner = spawner

    async def spawn_for_task(
        self,
        task_id: str,
        agent_id: str,
        phase_id: str,
        env_vars: dict[str, str],
        *,
        runtime: str = "claude",
        execution_mode: str = "implementation",
        image: Optional[str] = None,
        sandbox_session_token: Optional[str] = None,
    ) -> SandboxResult:
        sandbox_id = await self._spawner.spawn_for_task(
            task_id=task_id,
            agent_id=agent_id,
            phase_id=phase_id,
            runtime=runtime,
            execution_mode=execution_mode,
            extra_env=env_vars,
            sandbox_session_token=sandbox_session_token,
        )
        return SandboxResult(
            sandbox_id=sandbox_id,
            status="creating",
            connection_info={"provider": "daytona"},
        )

    async def terminate_sandbox(self, sandbox_id: str) -> None:
        await self._spawner.terminate_sandbox(sandbox_id)

    async def get_status(self, sandbox_id: str) -> SandboxStatus:
        try:
            info = self._spawner.get_sandbox_info(sandbox_id)
            return SandboxStatus(
                sandbox_id=sandbox_id,
                status=info.status if info else "unknown",
            )
        except Exception:
            return SandboxStatus(sandbox_id=sandbox_id, status="unknown")

    async def list_active(self) -> list[SandboxStatus]:
        try:
            active = getattr(self._spawner, "_active_sandboxes", {})
            return [
                SandboxStatus(sandbox_id=sid, status=getattr(info, "status", "unknown"))
                for sid, info in active.items()
            ]
        except Exception:
            return []

    # ─── Optional: hosted-editor tunnels (spec §15 §11) ────────────────────

    async def expose_port(self, sandbox_id: str, port: int) -> Optional[str]:
        """Return a public HTTPS URL for the given port on the sandbox.

        Uses Daytona SDK v0.119.0's `sandbox.get_preview_link(port)` (already
        used elsewhere in the spawner at daytona_spawner.py:1123). Returns
        None when the sandbox isn't in the active registry or the API call
        fails — callers treat None as "no editor URL available".
        """
        try:
            info = self._spawner.get_sandbox_info(sandbox_id)
            if info is None:
                return None
            sandbox = getattr(info, "sandbox", None)
            if sandbox is None:
                return None
            # get_preview_link is sync in the Daytona SDK; wrap in executor
            # to stay on the asyncio loop.
            import asyncio

            loop = asyncio.get_event_loop()
            preview = await loop.run_in_executor(
                None, lambda: sandbox.get_preview_link(port)
            )
            return getattr(preview, "url", None)
        except Exception:  # noqa: BLE001 — tunnel mint is best-effort
            return None

    # ─── Optional: workspace-scoped named volumes (spec §15 §4 #3) ─────────

    async def get_or_create_volume(self, volume_name: str) -> Optional[str]:
        """Return a Daytona volume id for the given name; create if missing.

        Uses `daytona.volume.get(name, create=True)` from v0.119.0. The
        returned id is what `CreateSandboxFrom{Snapshot,Image}Params.volumes`
        expects alongside a mount_path. Returns None on failure so the
        caller can fall back to "no volume" gracefully.
        """
        daytona = getattr(self._spawner, "_daytona", None) or getattr(
            self._spawner, "daytona", None
        )
        if daytona is None:
            return None
        try:
            import asyncio

            loop = asyncio.get_event_loop()
            volume = await loop.run_in_executor(
                None, lambda: daytona.volume.get(volume_name, create=True)
            )
            return getattr(volume, "id", None)
        except Exception:  # noqa: BLE001
            return None
