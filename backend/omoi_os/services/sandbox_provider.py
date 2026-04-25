"""Sandbox provider protocol for abstracting Daytona vs local Docker execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Optional, Any, runtime_checkable


@dataclass
class SandboxResult:
    """Result of spawning a sandbox."""

    sandbox_id: str
    status: str  # "creating" | "running" | "completed" | "failed" | "terminated"
    connection_info: dict[str, Any] = field(default_factory=dict)


@dataclass
class SandboxStatus:
    """Current status of a sandbox."""

    sandbox_id: str
    status: str
    started_at: Optional[str] = None
    error: Optional[str] = None


@runtime_checkable
class SandboxProvider(Protocol):
    """Protocol for sandbox lifecycle management.

    The tunnel + volume methods are optional — providers that can't expose
    ports (e.g. LocalDockerProvider) or don't support named volumes simply
    don't implement them. Callers use `hasattr(provider, 'expose_port')` /
    `hasattr(provider, 'mount_volume')` to feature-detect at spawn time.
    """

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
    ) -> SandboxResult: ...

    async def terminate_sandbox(self, sandbox_id: str) -> None: ...

    async def get_status(self, sandbox_id: str) -> SandboxStatus: ...

    async def list_active(self) -> list[SandboxStatus]: ...

    # --- Optional capability: port tunnels (spec §15 §11) ------------------
    # Providers that support hosted-editor tunnels implement `expose_port`
    # returning a public HTTPS URL for the given port. Callers use `hasattr`
    # detection because `Protocol` inheritance doesn't distinguish optional
    # methods.
    #
    # async def expose_port(self, sandbox_id: str, port: int) -> str: ...

    # --- Optional capability: named volumes (spec §15 §4 #3) ---------------
    # Providers that support workspace-scoped persistent volumes implement
    # `get_or_create_volume` returning a provider-specific volume id. The
    # sandbox creation call then references that id via volumes=[...].
    #
    # async def get_or_create_volume(self, volume_name: str) -> str: ...
