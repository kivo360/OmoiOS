"""omoi_os Modal provider — subclass of sandbox-agent-sdk's ModalProvider.

Adds opencode to the default sandbox-agent image and applies omoi_os-specific
defaults (app name, memory, timeout). Cross-replica reattach is inherited
from the base class's ``reconnect()`` which calls ``modal.Sandbox.from_id()``.

Kept deliberately thin: the SDK base class owns the lifecycle (create,
destroy, get_url, ensure_server, reconnect). This subclass only wires
omoi_os defaults into ``ModalProviderOptions`` at construction time.
"""

from __future__ import annotations

from typing import Any

from sandboxagent.providers.modal import (
    DEFAULT_AGENT_PORT,
    ModalProvider,
    ModalProviderOptions,
)
from sandboxagent.providers.shared import SANDBOX_AGENT_INSTALL_SCRIPT


OMOI_APP_NAME = "omoi-os-agents"
OMOI_DEFAULT_MEMORY_MIB = 4096
OMOI_DEFAULT_TIMEOUT_SECONDS = 60 * 60


def build_omoi_modal_image(*, base: str | None = None) -> Any:
    """Build the Modal image with sandbox-agent + opencode installed.

    Uses ``debian_slim`` as the base by default. The published
    ``rivetdev/sandbox-agent:0.5.0-rc.2-full`` registry image cannot be
    used directly — its ENTRYPOINT conflicts with Modal's
    ``Sandbox.create("sleep", "infinity", ...)`` arg pattern, killing
    the sandbox immediately on spawn (verified empirically in
    scripts/poof/probe_sdk_modal_*.py on 2026-04-26).

    Modal hashes the spec and caches the built image, so this is a
    one-time cost per (base, commands) tuple — every subsequent spawn
    skips the install entirely.
    """
    import modal

    if base is not None:
        img = modal.Image.from_registry(base)
    else:
        img = modal.Image.debian_slim().apt_install("curl", "ca-certificates", "git")

    return img.run_commands(
        # Install the SDK transport binary; the install script lives at
        # the same URL the SDK references via SANDBOX_AGENT_INSTALL_SCRIPT.
        f"curl -fsSL {SANDBOX_AGENT_INSTALL_SCRIPT} | sh",
        "sandbox-agent --version",
        # Install opencode + its workspace dirs so chat sessions can route
        # through opencode without paying install latency on cold spawn.
        "mkdir -p /root/.local/share/opencode /root/.config/opencode",
        "chmod 700 /root/.local/share/opencode",
        "curl -fsSL https://opencode.ai/install | bash",
        # Force install verification at image-build time so broken installs
        # surface in Modal build logs rather than at first sandbox.exec.
        "/root/.opencode/bin/opencode --version",
    )


class OmoiOsModalProvider(ModalProvider):
    """``ModalProvider`` configured for omoi_os agent sessions.

    - Uses a custom image with sandbox-agent + opencode pre-baked.
    - Defaults to ``omoi-os-agents`` app with 4 GiB memory, 1 h timeout.
    - Inherits cross-replica reattach via ``reconnect()`` from the base
      (calls ``modal.Sandbox.from_id()``).
    - The caller injects ``env_vars`` (BROKER_URL, SESSION_TOKEN, opencode/omo
      config blobs, etc.); these become a Modal Secret applied to every
      sandbox spawned by this provider.
    """

    def __init__(
        self,
        *,
        env_vars: dict[str, str] | None = None,
        app_name: str = OMOI_APP_NAME,
        agent_port: int = DEFAULT_AGENT_PORT,
        memory_mib: int = OMOI_DEFAULT_MEMORY_MIB,
        timeout_seconds: int = OMOI_DEFAULT_TIMEOUT_SECONDS,
        encrypted_ports: list[int] | None = None,
        image: Any | None = None,
    ) -> None:
        resolved_image = image if image is not None else build_omoi_modal_image()
        options = ModalProviderOptions(
            image=resolved_image,
            app_name=app_name,
            agent_port=agent_port,
            create={
                "secrets": dict(env_vars) if env_vars else {},
                "encrypted_ports": list(encrypted_ports) if encrypted_ports else [],
                "memory_mib": memory_mib,
                "timeout": timeout_seconds,
            },
        )
        super().__init__(options)
