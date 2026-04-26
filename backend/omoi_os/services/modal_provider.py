"""Modal-backed sandbox provider — peer of `DaytonaProvider`.

Implements the `SandboxProvider` protocol so the orchestrator and any
caller of the sandbox factory can swap from Daytona to Modal with a
single config flag (`sandbox.provider = "modal"`).
"""

from __future__ import annotations

from typing import Optional

from omoi_os.services.sandbox_provider import SandboxResult, SandboxStatus


class ModalProvider:
    """SandboxProvider backed by Modal sandboxes."""

    def __init__(self, spawner) -> None:
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
            status="running",
            connection_info={"provider": "modal"},
        )

    async def terminate_sandbox(self, sandbox_id: str) -> None:
        await self._spawner.terminate_sandbox(sandbox_id)

    async def get_status(self, sandbox_id: str) -> SandboxStatus:
        info = self._spawner.get_sandbox_info(sandbox_id)
        if info is None:
            return SandboxStatus(sandbox_id=sandbox_id, status="unknown")
        return SandboxStatus(
            sandbox_id=sandbox_id,
            status=info.status,
            started_at=info.started_at.isoformat() if info.started_at else None,
            error=info.error,
        )

    async def list_active(self) -> list[SandboxStatus]:
        active = getattr(self._spawner, "_sandboxes", {})
        return [
            SandboxStatus(
                sandbox_id=sid,
                status=getattr(info, "status", "unknown"),
            )
            for sid, info in active.items()
            if getattr(info, "status", None) in ("creating", "running")
        ]

    # ─── optional capabilities (parity with DaytonaProvider) ────────────────

    async def expose_port(self, sandbox_id: str, port: int) -> Optional[str]:
        """Return the public tunnel URL for a port declared at create time.

        Modal requires `encrypted_ports=[port, ...]` to be set when the
        sandbox is created. Tunnels are not openable after the fact. The
        spawner caches URLs in `info.extra_data['tunnel_urls']`; we return
        from there. Returns None if the port wasn't declared.
        """
        return await self._spawner.expose_port(sandbox_id, port)

    async def get_or_create_volume(self, volume_name: str) -> Optional[str]:
        return await self._spawner.get_or_create_volume(volume_name)
