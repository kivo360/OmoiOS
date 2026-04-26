"""`omoios providers` — manage credential bindings (list/add/delete).

Wraps the existing SDK `client.credentials` resource so the CLI is a
thin terminal surface over the same API surface dashboards consume.
"""

from __future__ import annotations

import asyncio
import json as _json
from typing import Any, Awaitable, Optional

import click

from omoios.cli._config import resolve_config


def _run_sdk(coro: Awaitable[Any]) -> Any:
    """Run an SDK coroutine, translating SDK exceptions into clean
    `click.ClickException` errors so the user sees a friendly message
    instead of a Python traceback."""
    from omoios.exceptions import OmoiOSError

    try:
        return asyncio.run(coro)
    except OmoiOSError as exc:
        raise click.ClickException(f"{type(exc).__name__}: {exc}") from exc


@click.group()
def providers() -> None:
    """Manage provider credentials bound to a workspace."""


# ─── omoios providers list ───────────────────────────────────────────────────


@providers.command("list")
@click.option(
    "--workspace",
    "workspace_id",
    required=True,
    metavar="<workspace_id>",
    help="Workspace ID to list credentials for.",
)
@click.option(
    "--json",
    "as_json",
    is_flag=True,
    help="Emit raw JSON instead of the human-friendly table.",
)
@click.pass_context
def list_cmd(
    ctx: click.Context,
    workspace_id: str,
    as_json: bool,
) -> None:
    """List credentials in a workspace."""
    cfg = resolve_config(
        api_base_url=ctx.obj.get("api_base_url"),
        api_key=ctx.obj.get("api_key"),
    )
    items = _run_sdk(_list(cfg.api_base_url, cfg.api_key, workspace_id))

    if as_json:
        click.echo(_json.dumps([_credential_to_dict(c) for c in items], indent=2))
        return

    if not items:
        click.echo(f"No credentials in workspace {workspace_id}.")
        return

    click.echo(f"{'ID':<38} {'NAME':<32} KIND")
    for c in items:
        click.echo(f"{str(c.id):<38} {c.name:<32} {_kind_label(c)}")


# ─── omoios providers add ────────────────────────────────────────────────────


@providers.command("add")
@click.option(
    "--workspace",
    "workspace_id",
    required=True,
    metavar="<workspace_id>",
    help="Workspace ID to bind the credential into.",
)
@click.option(
    "--name",
    required=True,
    help="Human-readable name (e.g. 'fireworks-prod').",
)
@click.option(
    "--key",
    "value",
    metavar="<value>",
    help=(
        "Credential value. If omitted, read from $OMOIOS_PROVIDER_KEY "
        "(safer than passing on the CLI)."
    ),
)
@click.option(
    "--kind",
    type=click.Choice(["bearer_secret", "oauth", "api_key"], case_sensitive=False),
    default="bearer_secret",
    show_default=True,
    help="BindingKind enum value — `bearer_secret` matches Fireworks/Anthropic.",
)
@click.pass_context
def add_cmd(
    ctx: click.Context,
    workspace_id: str,
    name: str,
    value: Optional[str],
    kind: str,
) -> None:
    """Create a new credential binding in a workspace."""
    import os

    secret = value or os.environ.get("OMOIOS_PROVIDER_KEY")
    if not secret:
        raise click.ClickException(
            "Pass --key <value> or set OMOIOS_PROVIDER_KEY in the environment."
        )

    cfg = resolve_config(
        api_base_url=ctx.obj.get("api_base_url"),
        api_key=ctx.obj.get("api_key"),
    )
    created = _run_sdk(
        _add(
            cfg.api_base_url,
            cfg.api_key,
            workspace_id=workspace_id,
            name=name,
            kind=kind,
            value=secret,
        )
    )
    click.echo(
        f"created binding {created.id} ({created.name}, kind={_kind_label(created)})"
    )


# ─── omoios providers delete ─────────────────────────────────────────────────


@providers.command("delete")
@click.argument("credential_id")
@click.option(
    "--yes", is_flag=True, help="Skip the confirmation prompt."
)
@click.pass_context
def delete_cmd(ctx: click.Context, credential_id: str, yes: bool) -> None:
    """Delete a credential binding by ID."""
    if not yes:
        click.confirm(
            f"Delete credential {credential_id}?", abort=True
        )
    cfg = resolve_config(
        api_base_url=ctx.obj.get("api_base_url"),
        api_key=ctx.obj.get("api_key"),
    )
    _run_sdk(_delete(cfg.api_base_url, cfg.api_key, credential_id))
    click.echo(f"deleted {credential_id}")


# ─── async impls (kept thin so the Click handlers are testable) ──────────────


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
