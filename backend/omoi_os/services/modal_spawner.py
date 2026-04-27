"""Modal-backed sandbox spawner — peer of `DaytonaSpawnerService`.

Why Modal: Daytona credits run out; Modal has free credits and a near-1:1
sandbox API. The OmoiOS sandbox abstraction (`SandboxProvider`) is small
enough that swapping the cloud backend is just a matter of wiring the same
12 SDK calls.

Mapping:

| Daytona                                  | Modal                                       |
|------------------------------------------|---------------------------------------------|
| `Daytona(DaytonaConfig(api_key=...))`    | `modal.Client()` (uses MODAL_TOKEN_*)       |
| `daytona.create(CreateSandboxFrom...)`   | `modal.Sandbox.create(app, image, ...)`     |
| `sandbox.id`                             | `sb.object_id`                              |
| `sandbox.process.exec(cmd)`              | `sb.exec(*cmd_list)`                        |
| `sandbox.fs.upload_file(path, content)`  | `with sb.open(path, "wb") as f: f.write()`  |
| `sandbox.fs.download_file(path)`         | `with sb.open(path, "rb") as f: f.read()`   |
| `sandbox.git.clone(url, path)`           | `sb.exec("git", "clone", url, path)`        |
| `sandbox.get_preview_link(port).url`     | `sb.tunnels()[port].url` (encrypted_ports=) |
| `sandbox.stop()`                         | `sb.terminate()`                            |
| `daytona.volume.get(name, create=True)`  | `modal.Volume.from_name(name, ...)`         |
| `VolumeMount(volumeId, mountPath)`       | `volumes={"/x": vol}` dict                  |

Env vars in Modal go through `modal.Secret.from_dict(env)` rather than a
flat `env_vars=` parameter — different mental model, mechanically
identical for our use case.
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from omoi_os.config import get_app_settings
from omoi_os.logging import get_logger
from omoi_os.models.environment import EnvironmentVersion
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now


logger = get_logger(__name__)


@dataclass
class ModalSandboxInfo:
    """Tracking record for a live Modal sandbox.

    Mirrors the parts of Daytona's `SandboxInfo` that the OmoiOS provider
    abstraction reads. We deliberately do NOT mirror the entire Daytona
    record — fields like `daytona_sandbox_id` are Daytona-specific.
    """

    sandbox_id: str
    task_id: str
    phase_id: str
    status: str = "creating"
    created_at: datetime = field(default_factory=utc_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    extra_data: Dict[str, Any] = field(default_factory=dict)


async def _run_sync(fn: Callable[[], Any]) -> Any:
    """Push a blocking SDK call to the default executor."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fn)


class ModalSpawnerService:
    """Spawn and track Modal sandboxes for OmoiOS agent tasks.

    Public surface deliberately matches the parts of `DaytonaSpawnerService`
    that `DaytonaProvider` and `ModalProvider` both call:

        - `spawn_for_task(...)`
        - `terminate_sandbox(sandbox_id)`
        - `get_sandbox_info(sandbox_id)`
        - `get_or_create_volume(name)`
        - `expose_port(sandbox_id, port)` — handled at create time on Modal,
          so this returns the cached URL from `extra_data`.
    """

    def __init__(
        self,
        db: Optional[DatabaseService] = None,
        event_bus: Optional[EventBusService] = None,
        mcp_server_url: str = "http://localhost:18000/mcp/",
        sandbox_image: str = "nikolaik/python-nodejs:python3.12-nodejs22",
        modal_app_name: str = "omoi-os-sandboxes",
        sandbox_timeout_seconds: int = 86_400,
        sandbox_idle_timeout_seconds: int = 1_800,
    ) -> None:
        self.db = db
        self.event_bus = event_bus
        self.mcp_server_url = mcp_server_url
        self.sandbox_image = sandbox_image
        self.modal_app_name = modal_app_name
        self.sandbox_timeout_seconds = sandbox_timeout_seconds
        self.sandbox_idle_timeout_seconds = sandbox_idle_timeout_seconds

        # In-memory tracking of active sandboxes (parity with Daytona spawner).
        self._sandboxes: Dict[str, ModalSandboxInfo] = {}
        self._task_to_sandbox: Dict[str, str] = {}
        # Modal SDK objects are imported lazily so `modal` doesn't have to be
        # installed for the rest of the service to import.
        self._modal: Any = None
        self._app: Any = None

    # ─── lazy SDK + app handles ─────────────────────────────────────────────

    def _ensure_modal(self) -> Any:
        if self._modal is None:
            try:
                import modal  # type: ignore
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError(
                    "modal package not installed. Add `modal>=0.69` to "
                    "backend deps to enable the Modal sandbox backend."
                ) from exc
            self._modal = modal
        return self._modal

    async def _get_app(self) -> Any:
        if self._app is not None:
            return self._app
        modal = self._ensure_modal()
        # `App.lookup(..., create_if_missing=True)` is idempotent: it
        # creates the named app on first use, then re-uses it. Safe to call
        # on every cold start.
        self._app = await _run_sync(
            lambda: modal.App.lookup(self.modal_app_name, create_if_missing=True)
        )
        return self._app

    # ─── env-var construction (small, focused) ──────────────────────────────

    def _build_env(
        self,
        *,
        task_id: str,
        agent_id: str,
        phase_id: str,
        execution_mode: str,
        sandbox_id: str,
        extra_env: Optional[Dict[str, str]],
        env_version: Optional[EnvironmentVersion],
        sandbox_session_token: Optional[str],
    ) -> Dict[str, str]:
        base_url = self.mcp_server_url.replace("/mcp", "").rstrip("/")
        env: Dict[str, str] = {
            "AGENT_ID": agent_id,
            "TASK_ID": task_id,
            "EXECUTION_MODE": execution_mode,
            "MCP_SERVER_URL": self.mcp_server_url,
            "CALLBACK_URL": base_url,
            "PHASE_ID": phase_id,
            "SANDBOX_ID": sandbox_id,
            "IS_SANDBOX": "1",
            "OMOIOS_API_URL": base_url,
            "OMOIOS_SANDBOX_BACKEND": "modal",
        }
        # Egress proxy wiring — same shape as the Daytona path.
        if (
            env_version
            and env_version.egress
            and env_version.egress.get("allowed_hosts")
        ):
            env["HTTPS_PROXY"] = "http://127.0.0.1:8888"
            env["HTTP_PROXY"] = "http://127.0.0.1:8888"
            env["NO_PROXY"] = "localhost,127.0.0.1,169.254.169.254"
            env["OMOIOS_EGRESS_ALLOWED_HOSTS"] = ",".join(
                env_version.egress["allowed_hosts"]
            )
        # Broker session token — same shape.
        if env_version and env_version.credentials:
            if sandbox_session_token:
                env["SESSION_TOKEN"] = sandbox_session_token
            env["BROKER_URL"] = f"{base_url}/broker"
            aliases = list(env_version.credentials.keys())
            env["OMOIOS_CREDENTIAL_ALIASES"] = ",".join(aliases)
            # Render opencode.json + oh-my-openagent.jsonc — bootstrap
            # writes them into ~/.config/opencode/ so the agent has a
            # provider surface (spec §14, smoke phase opencode_config).
            from omoi_os.services.opencode_config_renderer import (
                render_omo_config,
                render_opencode_config,
            )

            env["OMOIOS_OPENCODE_CONFIG"] = render_opencode_config(aliases)
            env["OMOIOS_OMO_CONFIG"] = render_omo_config(aliases)
        if extra_env:
            env.update(extra_env)
        return env

    # ─── public surface ─────────────────────────────────────────────────────

    async def spawn_for_task(
        self,
        task_id: str,
        agent_id: str,
        phase_id: str,
        agent_type: Optional[str] = None,
        extra_env: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None,
        runtime: str = "claude",
        execution_mode: str = "implementation",
        env_version: Optional[EnvironmentVersion] = None,
        sandbox_session_token: Optional[str] = None,
        exposed_ports: Optional[list[int]] = None,
        **_ignored: Any,
    ) -> str:
        """Spawn a Modal sandbox for a task. Returns the OmoiOS sandbox id.

        ``exposed_ports`` takes precedence over ``env_version.exposed_ports``
        — chat-mode SDK-direct sessions don't carry an env_version but still
        need port 4096 exposed for `opencode serve`. Either source produces
        a Modal `encrypted_ports=[…]` declaration; both are merged when
        both are present.
        """
        from uuid import uuid4

        modal = self._ensure_modal()
        app = await self._get_app()

        sandbox_id = f"omoios-{task_id[:8]}-{uuid4().hex[:6]}"

        # Avoid duplicate spawn if task already has a live sandbox.
        if task_id in self._task_to_sandbox:
            existing = self._task_to_sandbox[task_id]
            info = self._sandboxes.get(existing)
            if info and info.status in ("creating", "running"):
                logger.info(
                    "[MODAL_SPAWNER] reusing existing sandbox",
                    extra={"task_id": task_id, "sandbox_id": existing},
                )
                return existing

        info = ModalSandboxInfo(
            sandbox_id=sandbox_id,
            task_id=task_id,
            phase_id=phase_id,
        )
        self._sandboxes[sandbox_id] = info
        self._task_to_sandbox[task_id] = sandbox_id

        env = self._build_env(
            task_id=task_id,
            agent_id=agent_id,
            phase_id=phase_id,
            execution_mode=execution_mode,
            sandbox_id=sandbox_id,
            extra_env=extra_env,
            env_version=env_version,
            sandbox_session_token=sandbox_session_token,
        )

        # Image: pull from the configured registry. Mirrors Daytona's
        # `sandbox_image` default. Use `from_registry` so we don't need to
        # build anything for a smoke run — same image shape as Daytona.
        image_ref = (env_version and getattr(env_version, "image", None)) or (
            self.sandbox_image
        )
        # Bake the OpenCode bootstrap dirs into the image so they're present
        # the moment the sandbox becomes ready — mirrors the pre-built dirs
        # in Daytona's `omoios-omo-vnc` snapshot. Modal caches built images,
        # so this only adds latency on the first cold build per (image_ref,
        # commands) tuple.
        # Don't pass `add_python=` — our default base image already ships
        # Python, and Modal's symlink injection collides with /usr/local/bin/python.
        # Bake opencode into the image at build time. Modal hashes the
        # spec and caches the built image, so this is a one-time cost
        # per (image_ref, commands) tuple — every subsequent spawn skips
        # the install entirely. Validated empirically: install-on-spawn
        # is ~5-30s of dead time per session; pre-baked image makes
        # `opencode --version` a sub-3s call from a fresh sandbox.
        image = modal.Image.from_registry(image_ref).run_commands(
            "mkdir -p /root/.local/share/opencode /root/.config/opencode",
            "chmod 700 /root/.local/share/opencode",
            "curl -fsSL https://opencode.ai/install | bash",
            # Forces install verification at image-build time, so a
            # broken install surfaces here (visible in Modal build logs)
            # rather than silently at first sandbox.exec.
            "/root/.opencode/bin/opencode --version",
        )

        # Volumes: opt-in via `env_version.persistent_volume` flag, same
        # contract as `daytona_spawner.py` line ~1567.
        volumes: Dict[str, Any] = {}
        if (
            env_version is not None
            and getattr(env_version, "persistent_volume", False)
            and labels
            and labels.get("workspace_id")
        ):
            vol_name = f"ws-{labels['workspace_id']}"
            volumes["/workspace"] = await self._get_or_create_volume(vol_name)

        # Encrypted ports — declared at create time on Modal (see
        # daytona_spawner.py:1664). Merge any caller-supplied ports
        # (chat-mode passes [4096] for `opencode serve`) with whatever
        # the env_version declares; dedupe to keep Modal happy.
        merged_ports = list(exposed_ports or [])
        merged_ports.extend(getattr(env_version, "exposed_ports", []) or [])
        exposed_ports = sorted({p for p in merged_ports if isinstance(p, int)})

        # Single Modal Secret carrying every env var. Easier than juggling
        # named secrets per category.
        secret = modal.Secret.from_dict(env)

        # The sandbox needs a long-running command so it stays alive while
        # we exec into it. `sleep infinity` is the canonical idle command.
        sandbox = await _run_sync(
            lambda: modal.Sandbox.create(
                "sleep",
                "infinity",
                app=app,
                image=image,
                secrets=[secret],
                volumes=volumes,
                encrypted_ports=exposed_ports,
                timeout=self.sandbox_timeout_seconds,
            )
        )

        info.extra_data["modal_sandbox"] = sandbox
        info.extra_data["modal_object_id"] = sandbox.object_id
        info.status = "running"
        info.started_at = utc_now()

        # Render opencode.json + oh-my-openagent.jsonc directly to the
        # sandbox filesystem. Modal's container starts with `sleep
        # infinity` and never executes our bootstrap.sh, so we can't rely
        # on the env-var contract bootstrap reads — write the files now
        # while we have the sandbox handle. Skipped silently when no
        # provider config was rendered (e.g. bare smoke sandboxes).
        opencode_body = env.get("OMOIOS_OPENCODE_CONFIG")
        omo_body = env.get("OMOIOS_OMO_CONFIG")
        if opencode_body or omo_body:
            try:
                # Ensure the config dir exists. Modal `Image.run_commands`
                # bakes /root/.config/opencode at image-build time, but
                # mkdir -p is idempotent and cheap.
                await _run_sync(
                    lambda: sandbox.exec("mkdir", "-p", "/root/.config/opencode")
                )
                if opencode_body:
                    await _run_sync(
                        lambda: sandbox.filesystem.write_bytes(
                            opencode_body.encode("utf-8"),
                            "/root/.config/opencode/opencode.json",
                        )
                    )
                if omo_body:
                    await _run_sync(
                        lambda: sandbox.filesystem.write_bytes(
                            omo_body.encode("utf-8"),
                            "/root/.config/opencode/oh-my-openagent.jsonc",
                        )
                    )
                logger.info(
                    "[MODAL_SPAWNER] opencode config files written",
                    extra={
                        "sandbox_id": sandbox_id,
                        "wrote_opencode_json": bool(opencode_body),
                        "wrote_omo_jsonc": bool(omo_body),
                    },
                )
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.warning(
                    "[MODAL_SPAWNER] opencode config write failed",
                    extra={"sandbox_id": sandbox_id, "error": str(exc)},
                )

        # auth.json — Modal never runs bootstrap.sh, so the broker→
        # auth.json render path is dead. Resolve aliases inline against
        # the broker service and write the file directly. This is the
        # secret-delivery analog of the opencode.json write above.
        ws_id_label = (labels or {}).get("workspace_id")
        if env_version and env_version.credentials and ws_id_label:
            try:
                from uuid import UUID as _UUID

                from omoi_os.services.credential_broker import (
                    get_credential_broker_service,
                )
                from omoi_os.services.opencode_config_renderer import (
                    render_auth_json,
                )

                broker = get_credential_broker_service()
                resolved = await broker.resolve_aliases_for_spawn(
                    environment_version_id=env_version.id,
                    workspace_id=_UUID(ws_id_label)
                    if isinstance(ws_id_label, str)
                    else ws_id_label,
                )
                if resolved:
                    auth_body = render_auth_json(resolved)
                    await _run_sync(
                        lambda: sandbox.exec(
                            "mkdir", "-p", "/root/.local/share/opencode"
                        )
                    )
                    await _run_sync(
                        lambda: sandbox.filesystem.write_bytes(
                            auth_body.encode("utf-8"),
                            "/root/.local/share/opencode/auth.json",
                        )
                    )
                    logger.info(
                        "[MODAL_SPAWNER] auth.json written",
                        extra={
                            "sandbox_id": sandbox_id,
                            "alias_count": len(resolved),
                        },
                    )
            except Exception as exc:  # noqa: BLE001 — best-effort
                logger.warning(
                    "[MODAL_SPAWNER] auth.json write failed",
                    extra={"sandbox_id": sandbox_id, "error": str(exc)},
                )

        # Tunnel URLs for any exposed_ports. Modal returns these
        # synchronously after `create` completes.
        if exposed_ports:
            try:
                tunnels = await _run_sync(lambda: sandbox.tunnels())
                tunnel_urls = {
                    str(port): tunnels[port].url
                    for port in exposed_ports
                    if port in tunnels
                }
                if tunnel_urls:
                    info.extra_data["tunnel_urls"] = tunnel_urls
            except Exception as exc:  # noqa: BLE001 — tunnels are best-effort
                logger.warning(
                    "[MODAL_SPAWNER] tunnel collection failed",
                    extra={"sandbox_id": sandbox_id, "error": str(exc)},
                )

        logger.info(
            "[MODAL_SPAWNER] sandbox created",
            extra={
                "sandbox_id": sandbox_id,
                "modal_object_id": sandbox.object_id,
                "task_id": task_id,
                "image": image_ref,
                "exposed_ports": exposed_ports,
            },
        )
        return sandbox_id

    async def terminate_sandbox(self, sandbox_id: str) -> bool:
        info = self._sandboxes.get(sandbox_id)
        if info is None:
            return False
        sandbox = info.extra_data.get("modal_sandbox")
        if sandbox is not None:
            with contextlib.suppress(Exception):
                await _run_sync(lambda: sandbox.terminate())
        info.status = "terminated"
        info.completed_at = utc_now()
        # Remove the task→sandbox mapping so re-spawns work.
        for tid, sid in list(self._task_to_sandbox.items()):
            if sid == sandbox_id:
                self._task_to_sandbox.pop(tid, None)
        return True

    def get_sandbox_info(self, sandbox_id: str) -> Optional[ModalSandboxInfo]:
        return self._sandboxes.get(sandbox_id)

    # ─── optional capabilities ──────────────────────────────────────────────

    async def expose_port(self, sandbox_id: str, port: int) -> Optional[str]:
        """Return the tunnel URL for a port that was declared at create time.

        Modal does not allow exposing additional ports after sandbox
        creation. Callers should set `env_version.exposed_ports` at spawn
        time. We return the URL from `tunnel_urls` if it was collected.
        """
        info = self._sandboxes.get(sandbox_id)
        if info is None:
            return None
        urls = info.extra_data.get("tunnel_urls") or {}
        return urls.get(str(port))

    async def _get_or_create_volume(self, name: str) -> Any:
        modal = self._ensure_modal()
        return await _run_sync(
            lambda: modal.Volume.from_name(name, create_if_missing=True)
        )

    async def get_or_create_volume(self, name: str) -> Optional[str]:
        try:
            vol = await self._get_or_create_volume(name)
            return getattr(vol, "object_id", None) or name
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[MODAL_SPAWNER] volume create failed",
                extra={"volume_name": name, "error": str(exc)},
            )
            return None

    # ─── exec + filesystem (used by integration tests / debugging) ──────────

    async def register_foreign_sandbox(
        self,
        sandbox_id: str,
        modal_object_id: str,
        *,
        task_id: str,
        phase_id: str = "chat",
    ) -> bool:
        """Register a Modal sandbox that was created by another replica.

        Used by the cross-replica rehydration path in
        `modal_sandboxed_agent`: replica B receives a chat turn for a
        session whose sandbox was spawned by replica A, looks up the
        modal_object_id from `task.result`, and calls this to wire the
        foreign sandbox into the local spawner so subsequent
        `spawner.exec(sandbox_id, ...)` calls drive the right sandbox.

        Returns True if the rehydration succeeded; False if the Modal
        SDK couldn't find the sandbox (e.g. it was reaped).
        """
        if sandbox_id in self._sandboxes:
            return True  # Already attached.
        modal = self._ensure_modal()
        try:
            sandbox = await _run_sync(lambda: modal.Sandbox.from_id(modal_object_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[MODAL_SPAWNER] foreign sandbox lookup failed",
                extra={
                    "sandbox_id": sandbox_id,
                    "modal_object_id": modal_object_id,
                    "error": str(exc),
                },
            )
            return False
        info = ModalSandboxInfo(
            sandbox_id=sandbox_id,
            task_id=task_id,
            phase_id=phase_id,
            status="running",
            started_at=utc_now(),
        )
        info.extra_data["modal_sandbox"] = sandbox
        info.extra_data["modal_object_id"] = modal_object_id
        info.extra_data["foreign"] = True
        self._sandboxes[sandbox_id] = info
        self._task_to_sandbox[task_id] = sandbox_id
        return True

    async def exec(self, sandbox_id: str, *cmd: str) -> Dict[str, Any]:
        info = self._sandboxes.get(sandbox_id)
        if info is None:
            raise RuntimeError(f"unknown sandbox {sandbox_id}")
        sandbox = info.extra_data.get("modal_sandbox")
        if sandbox is None:
            raise RuntimeError(f"sandbox {sandbox_id} has no live handle")
        proc = await _run_sync(lambda: sandbox.exec(*cmd))
        stdout = await _run_sync(lambda: proc.stdout.read())
        stderr = await _run_sync(lambda: proc.stderr.read())
        return_code = await _run_sync(lambda: proc.wait())
        return {"stdout": stdout, "stderr": stderr, "exit_code": return_code}

    async def upload_file(self, sandbox_id: str, path: str, content: bytes) -> None:
        info = self._sandboxes.get(sandbox_id)
        if info is None:
            raise RuntimeError(f"unknown sandbox {sandbox_id}")
        sandbox = info.extra_data.get("modal_sandbox")
        if sandbox is None:
            raise RuntimeError(f"sandbox {sandbox_id} has no live handle")
        # Modal's sync `Sandbox.filesystem` wraps the async impl, so the
        # method itself is sync and must NOT be awaited. Run on the executor
        # to keep the asyncio loop free. Signature: (data, remote_path) —
        # legacy `open()` is deprecated for removal 2026-03.
        await _run_sync(lambda: sandbox.filesystem.write_bytes(content, path))

    async def download_file(self, sandbox_id: str, path: str) -> bytes:
        info = self._sandboxes.get(sandbox_id)
        if info is None:
            raise RuntimeError(f"unknown sandbox {sandbox_id}")
        sandbox = info.extra_data.get("modal_sandbox")
        if sandbox is None:
            raise RuntimeError(f"sandbox {sandbox_id} has no live handle")
        return await _run_sync(lambda: sandbox.filesystem.read_bytes(path))


# ─── module-level singleton accessor (mirrors get_daytona_spawner) ──────────


_spawner_instance: Optional[ModalSpawnerService] = None


def get_modal_spawner(
    db: Optional[DatabaseService] = None,
    event_bus: Optional[EventBusService] = None,
) -> ModalSpawnerService:
    """Return the process-wide ModalSpawnerService, lazily constructed."""
    global _spawner_instance
    if _spawner_instance is None:
        settings = get_app_settings()
        sandbox_settings = settings.sandbox
        api_base = getattr(sandbox_settings, "local_api_base_url", None) or (
            "http://localhost:18000"
        )
        _spawner_instance = ModalSpawnerService(
            db=db,
            event_bus=event_bus,
            mcp_server_url=f"{api_base.rstrip('/')}/mcp/",
            sandbox_image=getattr(
                sandbox_settings,
                "local_image",
                "nikolaik/python-nodejs:python3.12-nodejs22",
            ),
            modal_app_name=getattr(
                sandbox_settings, "modal_app_name", "omoi-os-sandboxes"
            ),
        )
    return _spawner_instance
