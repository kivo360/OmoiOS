"""`omoios artifacts` — list, fetch, and download session artifacts.

Used by spec §18 #13 (shareable replay) and #30 (no-code workflow
runners that hand the artifact URL to the next step).
"""

from __future__ import annotations

import json as _json
import mimetypes
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


@artifacts_app.command(name="upload")
def upload_cmd(
    path: Annotated[
        Optional[str],
        Parameter(help="File path to upload. Omit when using --stdin."),
    ] = None,
    workspace: Annotated[
        Optional[str],
        Parameter(
            name=["--workspace", "-w"],
            env_var="OMOIOS_WORKSPACE_ID",
            help="Workspace to upload into.",
        ),
    ] = None,
    stdin: Annotated[
        bool,
        Parameter(
            name="--stdin",
            help="Read bytes from stdin instead of a file path.",
        ),
    ] = False,
    name: Annotated[
        Optional[str],
        Parameter(
            name="--name",
            help="Filename to record. Defaults to basename(path) or 'stdin.bin'.",
        ),
    ] = None,
    content_type: Annotated[
        Optional[str],
        Parameter(
            name="--content-type",
            help="MIME type override. Auto-detected from extension when omitted.",
        ),
    ] = None,
    session: Annotated[
        Optional[str],
        Parameter(
            name=["--session", "-s"],
            help="Optional session ID to record in metadata.",
        ),
    ] = None,
    metadata_pairs: Annotated[
        Optional[list[str]],
        Parameter(
            name="--metadata",
            help="Extra KEY=VALUE metadata pairs (repeatable).",
        ),
    ] = None,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Upload a file as an artifact in a workspace.

    Reads the entire file into memory (the underlying SDK takes bytes,
    not a stream). For very large files, prefer chunked uploads when
    the SDK grows that surface. Use `--stdin` to pipe bytes in.
    """
    if not workspace:
        raise CliError("--workspace <id> (or $OMOIOS_WORKSPACE_ID) is required.")
    if stdin:
        blob = sys.stdin.buffer.read()
        resolved_name = name or "stdin.bin"
    else:
        if not path:
            raise CliError(
                "Pass a file path, or use --stdin to pipe bytes in."
            )
        p = Path(path)
        if not p.exists():
            raise CliError(f"file not found: {path}")
        blob = p.read_bytes()
        resolved_name = name or p.name

    mime = content_type or _guess_mime(resolved_name)

    metadata: dict[str, str] = {}
    if session:
        metadata["session_id"] = session
    for pair in metadata_pairs or []:
        if "=" not in pair:
            raise CliError(f"--metadata expected KEY=VALUE, got {pair!r}")
        k, v = pair.split("=", 1)
        metadata[k] = v

    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    console.print(
        f"[dim]uploading {_human_size(len(blob))} as "
        f"[cyan]{resolved_name}[/cyan]…[/dim]"
    )
    artifact = run_sdk(
        _upload(
            cfg.api_base_url,
            cfg.api_key,
            blob,
            workspace,
            resolved_name,
            mime,
            metadata or None,
        )
    )
    ok(
        f"uploaded [bold]{artifact.id}[/bold] · "
        f"{getattr(artifact, 'name', resolved_name)} "
        f"({_human_size(len(blob))})"
    )


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


async def _upload(
    api_base_url,
    api_key,
    blob,
    workspace_id,
    filename,
    content_type,
    metadata,
):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=None
    ) as client:
        return await client.artifacts.upload(
            file_content=blob,
            workspace_id=workspace_id,
            filename=filename,
            content_type=content_type,
            metadata=metadata,
        )


def _guess_mime(filename: str) -> Optional[str]:
    mime, _ = mimetypes.guess_type(filename)
    return mime


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
