"""Factory for creating the appropriate SandboxProvider based on config."""

from __future__ import annotations
from omoi_os.services.sandbox_provider import SandboxProvider


def create_sandbox_provider(db=None, event_bus=None, **kwargs) -> SandboxProvider:
    """Create SandboxProvider based on config."""
    from omoi_os.config import get_app_settings

    settings = get_app_settings()
    provider_type = settings.sandbox.provider

    if provider_type == "local":
        from omoi_os.services.local_docker_provider import LocalDockerProvider

        return LocalDockerProvider(
            image=settings.sandbox.local_image,
            mount_workspace=settings.sandbox.local_mount_workspace,
            api_base_url=settings.sandbox.local_api_base_url,
        )
    if provider_type == "modal":
        from omoi_os.services.modal_provider import ModalProvider
        from omoi_os.services.modal_spawner import get_modal_spawner

        spawner = get_modal_spawner(db=db, event_bus=event_bus)
        return ModalProvider(spawner)
    # Default: Daytona
    if db is None or event_bus is None:
        raise ValueError("DaytonaProvider requires db and event_bus")
    from omoi_os.services.daytona_spawner import get_daytona_spawner
    from omoi_os.services.daytona_provider import DaytonaProvider

    spawner = get_daytona_spawner(db=db, event_bus=event_bus)
    return DaytonaProvider(spawner)
