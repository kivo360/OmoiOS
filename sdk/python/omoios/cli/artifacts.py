"""`omoios artifacts` — list, fetch, and download session artifacts.

Used by spec §18 #13 (shareable replay) and #30 (no-code workflow
runners that hand the artifact URL to the next step).
"""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path
from typing import Annotated, Optional

from cyclopts import App, Parameter
from rich.table import Table

from omoios.cli._config import resolve_config
from omoios.cli._sdk import run_sdk
from omoios.cli._ui import CliError, console, ok


artifacts_app = App(
    name="artifacts",
    help="List and download session artifacts.",
)


@artifacts_app.command(name="list")
def list_cmd(
    workspace: Annotated[
        str,
        Parameter(
            name=["--workspace", "-w"],
            env_var="OMOIOS_WORKSPACE_ID",
            help="Workspace ID to scope to.",
        ),
    ],
    session: Annotated[
        Optional[str],
        Parameter(
            name=["--session", "-s"],
            help="Optional session-id post-filter applied client-side.",
        ),
    ] = None,
    json_output: Annotated[bool, Parameter(name="--json")] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """List artifacts in a workspace (optional `--session` post-filter)."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    items = run_sdk(_list(cfg.api_base_url, cfg.api_key, workspace))
    if session:
        items = [a for a in items if str(getattr(a, "session_id", "")) == session]

    if json_output:
        console.print_json(_json.dumps([_to_dict(a) for a in items]))
        return
    if not items:
        console.print("No artifacts.")
        return

    table = Table(title=f"artifacts ({len(items)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("KIND", style="cyan")
    table.add_column("NAME", style="white")
    table.add_column("SIZE", style="dim")
    for a in items:
        table.add_row(
            str(a.id),
            getattr(a, "kind", "?") or "?",
            getattr(a, "name", "") or "",
            _human_size(getattr(a, "size_bytes", None)),
        )
    console.print(table)


@artifacts_app.command(name="get")
def get_cmd(
    artifact_id: Annotated[str, Parameter(help="Artifact ID.")],
    json_output: Annotated[bool, Parameter(name="--json")] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Show metadata for one artifact."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    a = run_sdk(_get(cfg.api_base_url, cfg.api_key, artifact_id))
    if json_output:
        console.print_json(_json.dumps(_to_dict(a)))
        return
    console.print(f"[bold]{a.id}[/bold] · {getattr(a, 'name', '')}")
    for k in ("kind", "session_id", "size_bytes", "created_at", "url"):
        v = getattr(a, k, None)
        if v is not None:
            console.print(f"  [dim]{k}:[/dim] {v}")


@artifacts_app.command(name="download")
def download_cmd(
    artifact_id: Annotated[str, Parameter(help="Artifact ID.")],
    output: Annotated[
        Optional[str],
        Parameter(
            name=["--output", "-o"],
            help="Output file path. Use '-' for stdout. Defaults to <artifact_id>.bin.",
        ),
    ] = None,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Download the raw bytes of an artifact."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    blob: bytes = run_sdk(_download(cfg.api_base_url, cfg.api_key, artifact_id))

    target = output or f"{artifact_id}.bin"
    if target == "-":
        sys.stdout.buffer.write(blob)
        sys.stdout.buffer.flush()
        return
    Path(target).write_bytes(blob)
    ok(f"wrote {len(blob)} bytes → [dim]{target}[/dim]")


# ─── async impls ─────────────────────────────────────────────────────────────


async def _list(api_base_url, api_key, workspace_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.artifacts.list(workspace_id=workspace_id)


async def _get(api_base_url, api_key, artifact_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.artifacts.get(artifact_id)


async def _download(api_base_url, api_key, artifact_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=None
    ) as client:
        return await client.artifacts.download(artifact_id)


# ─── helpers ─────────────────────────────────────────────────────────────────


def _to_dict(a) -> dict:
    return {
        "id": str(a.id),
        "kind": getattr(a, "kind", None),
        "name": getattr(a, "name", None),
        "session_id": str(getattr(a, "session_id", "") or "") or None,
        "size_bytes": getattr(a, "size_bytes", None),
        "created_at": str(getattr(a, "created_at", "") or "") or None,
    }


def _human_size(n: Optional[int]) -> str:
    if n is None:
        return "—"
    for unit in ("B", "K", "M", "G"):
        if n < 1024:
            return f"{n}{unit}"
        n //= 1024
    return f"{n}T"
