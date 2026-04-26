"""`omoios providers` — manage credential bindings (list/add/delete).

Wraps the SDK `client.credentials` resource so the CLI is a thin
terminal surface over the same API surface dashboards consume.
"""

from __future__ import annotations

import asyncio
import json as _json
import os
from typing import Annotated, Any, Awaitable, Literal, Optional

from cyclopts import App, Parameter
from rich.prompt import Confirm
from rich.table import Table

from omoios.cli._config import resolve_config
from omoios.cli._ui import CliError, console, ok


providers_app = App(
    name="providers",
    help="Manage provider credentials bound to a workspace.",
)


# ─── shared plumbing ─────────────────────────────────────────────────────────


def _run_sdk(coro: Awaitable[Any]) -> Any:
    """Run an SDK coroutine, translating SDK exceptions into clean
    `CliError`s with actionable hints so the user sees a friendly
    message instead of a Python traceback."""
    from omoios.exceptions import AuthError, NotFoundError, OmoiOSError

    try:
        return asyncio.run(coro)
    except AuthError as exc:
        raise CliError(
            f"AuthError: {exc}\n"
            "  hint: your API key is rejected. Run `omoios signup` to mint a "
            "fresh one, or check $OMOIOS_PLATFORM_API_KEY."
        ) from exc
    except NotFoundError as exc:
        raise CliError(
            f"NotFoundError: {exc}\n"
            "  hint: double-check the workspace / credential ID — "
            "`omoios providers list --workspace <id>` shows what exists."
        ) from exc
    except OmoiOSError as exc:
        raise CliError(f"{type(exc).__name__}: {exc}") from exc


# ─── omoios providers list ───────────────────────────────────────────────────


@providers_app.command(name="list")
def list_cmd(
    workspace: Annotated[
        str,
        Parameter(
            name=["--workspace", "-w"],
            help="Workspace ID to list credentials for.",
        ),
    ],
    json_output: Annotated[
        bool,
        Parameter(
            name="--json",
            help="Emit raw JSON instead of the rich table.",
        ),
    ] = False,
    api_base_url: Annotated[
        Optional[str],
        Parameter(
            name="--api-base-url",
            env_var="OMOIOS_API_BASE_URL",
            show_env_var=True,
        ),
    ] = None,
    api_key: Annotated[
        Optional[str],
        Parameter(
            name="--api-key",
            env_var="OMOIOS_PLATFORM_API_KEY",
            show_env_var=True,
        ),
    ] = None,
) -> None:
    """List credentials in a workspace."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    items = _run_sdk(_list(cfg.api_base_url, cfg.api_key, workspace))

    if json_output:
        console.print_json(_json.dumps([_credential_to_dict(c) for c in items]))
        return

    if not items:
        console.print(f"No credentials in workspace {workspace}.")
        return

    table = Table(title=f"credentials · workspace {workspace}", show_lines=False)
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("NAME", style="cyan")
    table.add_column("KIND", style="green")
    for c in items:
        table.add_row(str(c.id), c.name, _kind_label(c))
    console.print(table)


# ─── omoios providers add ────────────────────────────────────────────────────


@providers_app.command(name="add")
def add_cmd(
    workspace: Annotated[
        str,
        Parameter(
            name=["--workspace", "-w"],
            help="Workspace ID to bind the credential into.",
        ),
    ],
    name: Annotated[
        str,
        Parameter(name="--name", help="Human-readable name (e.g. 'fireworks-prod')."),
    ],
    key: Annotated[
        Optional[str],
        Parameter(
            name="--key",
            help=(
                "Credential value. If omitted, read from $OMOIOS_PROVIDER_KEY "
                "(safer than passing on the CLI)."
            ),
        ),
    ] = None,
    kind: Annotated[
        Literal["bearer_secret", "oauth", "api_key"],
        Parameter(
            name="--kind",
            help="BindingKind — `bearer_secret` matches Fireworks/Anthropic.",
        ),
    ] = "bearer_secret",
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Create a new credential binding in a workspace."""
    secret = key or os.environ.get("OMOIOS_PROVIDER_KEY")
    if not secret:
        raise CliError(
            "Pass --key <value> or set OMOIOS_PROVIDER_KEY in the environment."
        )

    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    created = _run_sdk(
        _add(
            cfg.api_base_url,
            cfg.api_key,
            workspace_id=workspace,
            name=name,
            kind=kind,
            value=secret,
        )
    )
    ok(
        f"created binding [bold]{created.id}[/bold] "
        f"({created.name}, kind={_kind_label(created)})"
    )


# ─── omoios providers delete ─────────────────────────────────────────────────


@providers_app.command(name="delete")
def delete_cmd(
    credential_id: Annotated[
        str, Parameter(help="UUID of the credential binding to delete.")
    ],
    yes: Annotated[
        bool,
        Parameter(name=["--yes", "-y"], help="Skip the confirmation prompt."),
    ] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Delete a credential binding by ID."""
    if not yes:
        confirmed = Confirm.ask(
            f"Delete credential [bold]{credential_id}[/bold]?", default=False
        )
        if not confirmed:
            console.print("[yellow]Aborted.[/yellow]")
            raise CliError("aborted by user", code=1)

    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    _run_sdk(_delete(cfg.api_base_url, cfg.api_key, credential_id))
    ok(f"deleted [bold]{credential_id}[/bold]")


# ─── async impls (kept thin so the command bodies stay readable) ─────────────


async def _list(api_base_url: str, api_key: str, workspace_id: str):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.credentials.list(workspace_id=workspace_id)


async def _add(
    api_base_url: str,
    api_key: str,
    *,
    workspace_id: str,
    name: str,
    kind: str,
    value: str,
):
    from omoios import AsyncOmoiOSClient
    from omoios.types import BindingKind, CreateCredentialRequest

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.credentials.create(
            CreateCredentialRequest(
                workspace_id=workspace_id,
                kind=BindingKind(kind.lower()),
                name=name,
                value=value,
            )
        )


async def _delete(api_base_url: str, api_key: str, credential_id: str) -> None:
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        await client.credentials.delete(credential_id)


# ─── output helpers ──────────────────────────────────────────────────────────


def _credential_to_dict(c) -> dict:
    return {
        "id": str(c.id),
        "name": c.name,
        "kind": _kind_label(c),
        "workspace_id": getattr(c, "workspace_id", None),
    }


def _kind_label(c) -> str:
    kind = getattr(c, "kind", None)
    return getattr(kind, "value", str(kind) if kind else "unknown")
