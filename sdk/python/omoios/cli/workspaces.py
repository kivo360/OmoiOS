"""`omoios workspaces` — workspace CRUD + settings.

The SDK's `WorkspacesResource` only exposes settings get/update today;
list/create/delete go through direct HTTP because the routes exist
(see `backend/omoi_os/api/routes/workspaces.py`) but haven't been
wrapped on the SDK side. This is the same trade-off the smoke scripts
make.
"""

from __future__ import annotations

import json as _json
import time
from typing import Annotated, Any, Optional

import httpx
from cyclopts import App, Parameter
from rich.prompt import Confirm
from rich.table import Table

from omoios.cli._config import resolve_config
from omoios.cli._ui import CliError, console, ok


workspaces_app = App(
    name="workspaces",
    help="List, create, get, and delete workspaces in your org.",
)


def _client(api_base_url: str, api_key: str) -> httpx.Client:
    return httpx.Client(
        base_url=api_base_url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15.0,
    )


def _check(resp: httpx.Response, what: str) -> Any:
    if resp.status_code in (200, 201, 204):
        return resp.json() if resp.content and resp.status_code != 204 else None
    if resp.status_code == 401:
        raise CliError(
            f"{what} failed: 401 unauthorized — `omoios whoami` to confirm key."
        )
    if resp.status_code == 404:
        raise CliError(f"{what} failed: 404 not found")
    raise CliError(f"{what} failed: {resp.status_code} {resp.text[:200]}")


@workspaces_app.command(name="list")
def list_cmd(
    json_output: Annotated[
        bool, Parameter(name="--json", help="Emit JSON instead of a table.")
    ] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """List workspaces visible to the current key."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    with _client(cfg.api_base_url, cfg.api_key) as c:
        items = _check(c.get("/api/v1/workspaces"), "workspaces list")

    if isinstance(items, dict):
        items = items.get("items", [])
    items = items or []

    if json_output:
        console.print_json(_json.dumps(items))
        return
    if not items:
        console.print("No workspaces.")
        return

    table = Table(title=f"workspaces ({len(items)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("NAME", style="cyan")
    table.add_column("SLUG", style="white")
    table.add_column("DEFAULT ENV", style="dim", no_wrap=True)
    for w in items:
        table.add_row(
            str(w.get("id", "")),
            str(w.get("name", "")),
            str(w.get("slug", "")),
            str(w.get("default_environment_id") or "—"),
        )
    console.print(table)


@workspaces_app.command(name="get")
def get_cmd(
    workspace_id: Annotated[str, Parameter(help="Workspace ID.")],
    json_output: Annotated[bool, Parameter(name="--json")] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Fetch one workspace by ID."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    with _client(cfg.api_base_url, cfg.api_key) as c:
        body = _check(c.get(f"/api/v1/workspaces/{workspace_id}"), "workspace get")

    if json_output:
        console.print_json(_json.dumps(body))
        return
    console.print(f"[bold]{body.get('id')}[/bold] {body.get('name')}")
    for k in ("slug", "organization_id", "default_environment_id", "created_at"):
        v = body.get(k)
        if v is not None:
            console.print(f"  [dim]{k}:[/dim] {v}")


@workspaces_app.command(name="create")
def create_cmd(
    name: Annotated[str, Parameter(help="Workspace name.")],
    org: Annotated[
        Optional[str],
        Parameter(
            name=["--org", "--org-id"],
            env_var="OMOIOS_TEST_ORG_ID",
            help="Organization ID (env: OMOIOS_TEST_ORG_ID).",
        ),
    ] = None,
    slug: Annotated[
        Optional[str],
        Parameter(name="--slug", help="URL slug. Defaults to name + epoch."),
    ] = None,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Create a new workspace in an org."""
    if not org:
        raise CliError("Pass --org <id> or set $OMOIOS_TEST_ORG_ID.")
    payload = {
        "name": name,
        "slug": slug or f"{name.lower().replace(' ', '-')}-{int(time.time())}",
        "org_id": org,
    }
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    with _client(cfg.api_base_url, cfg.api_key) as c:
        body = _check(
            c.post("/api/v1/workspaces", json=payload), "workspace create"
        )
    ok(f"created workspace [bold]{body.get('id')}[/bold] ({body.get('name')})")


@workspaces_app.command(name="delete")
def delete_cmd(
    workspace_id: Annotated[str, Parameter(help="Workspace ID to delete.")],
    yes: Annotated[
        bool, Parameter(name=["--yes", "-y"], help="Skip confirmation.")
    ] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Delete a workspace. CASCADEs to its sandboxes — be careful."""
    if not yes and not Confirm.ask(
        f"Delete workspace [bold]{workspace_id}[/bold]?", default=False
    ):
        raise CliError("aborted by user")
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    with _client(cfg.api_base_url, cfg.api_key) as c:
        _check(c.delete(f"/api/v1/workspaces/{workspace_id}"), "workspace delete")
    ok(f"deleted [bold]{workspace_id}[/bold]")
