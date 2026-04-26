"""`omoios connections` — list/remove third-party OAuth connections.

The SDK surface is `list / remove / oauth_url`. `oauth_url` is a
provider-specific URL the user opens in a browser to grant the
platform OAuth access (e.g. GitHub repo scopes beyond what device-flow
already gave us).
"""

from __future__ import annotations

import json as _json
from typing import Annotated, Optional

from cyclopts import App, Parameter
from rich.prompt import Confirm
from rich.table import Table

from omoios.cli._config import resolve_config
from omoios.cli._sdk import run_sdk
from omoios.cli._ui import CliError, console, ok


connections_app = App(
    name="connections",
    help="Inspect and remove third-party OAuth connections.",
)


@connections_app.command(name="list")
def list_cmd(
    json_output: Annotated[bool, Parameter(name="--json")] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """List third-party providers connected to the current account."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    items = run_sdk(_list(cfg.api_base_url, cfg.api_key))

    if json_output:
        console.print_json(_json.dumps(items))
        return
    if not items:
        console.print("No connected providers.")
        return

    table = Table(title=f"connections ({len(items)})")
    table.add_column("PROVIDER", style="cyan")
    table.add_column("SCOPES", style="white")
    table.add_column("CONNECTED AT", style="dim")
    for c in items:
        scopes = c.get("scopes") or c.get("granted_scopes") or []
        if isinstance(scopes, list):
            scopes = ", ".join(scopes)
        table.add_row(
            str(c.get("provider", "?")),
            str(scopes or "—"),
            str(c.get("connected_at") or c.get("created_at") or "—"),
        )
    console.print(table)


@connections_app.command(name="oauth-url")
def oauth_url_cmd(
    provider: Annotated[
        str,
        Parameter(help="Provider id (e.g. 'github', 'gitlab', 'google')."),
    ],
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Print the OAuth URL to start a connection (open in browser)."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    url = run_sdk(_oauth_url(cfg.api_base_url, cfg.api_key, provider))
    console.print(url)


@connections_app.command(name="remove")
def remove_cmd(
    provider: Annotated[str, Parameter(help="Provider id to disconnect.")],
    yes: Annotated[bool, Parameter(name=["--yes", "-y"])] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Disconnect a provider (revokes stored OAuth tokens)."""
    if not yes and not Confirm.ask(
        f"Remove [bold]{provider}[/bold] connection?", default=False
    ):
        raise CliError("aborted by user")
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    run_sdk(_remove(cfg.api_base_url, cfg.api_key, provider))
    ok(f"removed connection [bold]{provider}[/bold]")


# ─── async impls ─────────────────────────────────────────────────────────────


async def _list(api_base_url, api_key):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.connections.list()


async def _remove(api_base_url, api_key, provider):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        await client.connections.remove(provider)


async def _oauth_url(api_base_url, api_key, provider):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.connections.oauth_url(provider)
