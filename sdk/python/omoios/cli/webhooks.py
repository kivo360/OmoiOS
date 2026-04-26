"""`omoios webhooks` — register HTTP delivery endpoints (spec §18 #1, #4, #6).

Webhooks let the platform fan events out to external systems (Slack
bots, Linear triage, Stripe billing). The SDK exposes the full CRUD
surface; this is a thin Rich veneer.
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


webhooks_app = App(
    name="webhooks",
    help="Register and inspect outbound webhook subscriptions.",
)


@webhooks_app.command(name="list")
def list_cmd(
    org: Annotated[
        Optional[str],
        Parameter(
            name=["--org", "--org-id"],
            env_var="OMOIOS_TEST_ORG_ID",
            help="Organization ID (env: OMOIOS_TEST_ORG_ID).",
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
    """List webhook subscriptions for an org."""
    if not org:
        raise CliError("Pass --org <id> or set $OMOIOS_TEST_ORG_ID.")
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    items = run_sdk(_list(cfg.api_base_url, cfg.api_key, org))
    if json_output:
        console.print_json(_json.dumps([_to_dict(w) for w in items]))
        return
    if not items:
        console.print("No webhook subscriptions.")
        return

    table = Table(title=f"webhooks ({len(items)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("URL", style="cyan")
    table.add_column("EVENTS", style="white")
    table.add_column("ACTIVE", style="dim")
    for w in items:
        table.add_row(
            str(w.id),
            getattr(w, "url", ""),
            ", ".join(getattr(w, "events", []) or []),
            "yes" if getattr(w, "active", True) else "no",
        )
    console.print(table)


@webhooks_app.command(name="create")
def create_cmd(
    url: Annotated[str, Parameter(help="Endpoint to POST events to.")],
    events: Annotated[
        list[str],
        Parameter(
            name=["--event", "-e"],
            help="Event type(s) to subscribe to. Repeat for multiple.",
        ),
    ],
    description: Annotated[str, Parameter(name="--description")] = "",
    org: Annotated[
        Optional[str],
        Parameter(
            name=["--org", "--org-id"],
            env_var="OMOIOS_TEST_ORG_ID",
            help="Organization ID (env: OMOIOS_TEST_ORG_ID).",
        ),
    ] = None,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Register a new webhook subscription."""
    if not events:
        raise CliError("Pass at least one --event TYPE.")
    if not org:
        raise CliError("Pass --org <id> or set $OMOIOS_TEST_ORG_ID.")
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    sub = run_sdk(
        _create(cfg.api_base_url, cfg.api_key, org, url, events, description)
    )
    ok(f"created webhook [bold]{sub.id}[/bold] → {url}")


@webhooks_app.command(name="delete")
def delete_cmd(
    webhook_id: Annotated[str, Parameter(help="Webhook subscription ID.")],
    yes: Annotated[bool, Parameter(name=["--yes", "-y"])] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Delete a webhook subscription."""
    if not yes and not Confirm.ask(
        f"Delete webhook [bold]{webhook_id}[/bold]?", default=False
    ):
        raise CliError("aborted by user")
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    run_sdk(_delete(cfg.api_base_url, cfg.api_key, webhook_id))
    ok(f"deleted [bold]{webhook_id}[/bold]")


@webhooks_app.command(name="deliveries")
def deliveries_cmd(
    webhook_id: Annotated[str, Parameter(help="Webhook subscription ID.")],
    json_output: Annotated[bool, Parameter(name="--json")] = False,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Show recent delivery attempts for a webhook (debugging aid)."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    items = run_sdk(_deliveries(cfg.api_base_url, cfg.api_key, webhook_id))
    if json_output:
        console.print_json(_json.dumps([_delivery_to_dict(d) for d in items]))
        return
    if not items:
        console.print("No deliveries recorded.")
        return

    table = Table(title=f"deliveries · webhook {webhook_id}")
    table.add_column("AT", style="dim", no_wrap=True)
    table.add_column("STATUS", style="cyan")
    table.add_column("EVENT", style="white")
    table.add_column("ATTEMPTS", style="dim")
    for d in items:
        table.add_row(
            str(getattr(d, "delivered_at", "") or "—"),
            str(getattr(d, "status", "?")),
            str(getattr(d, "event_type", "?")),
            str(getattr(d, "attempt_count", 1)),
        )
    console.print(table)


# ─── async impls ─────────────────────────────────────────────────────────────


async def _list(api_base_url, api_key, org_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.webhooks.list(org_id)


async def _create(api_base_url, api_key, org_id, url, events, description):
    from omoios import AsyncOmoiOSClient
    from omoios.types import CreateWebhookRequest, WebhookEvent

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.webhooks.create(
            org_id,
            CreateWebhookRequest(
                url=url,
                events=[WebhookEvent(e) for e in events],
                description=description or None,
            ),
        )


async def _delete(api_base_url, api_key, webhook_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        await client.webhooks.delete(webhook_id)


async def _deliveries(api_base_url, api_key, webhook_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.webhooks.list_deliveries(webhook_id)


def _to_dict(w) -> dict:
    return {
        "id": str(w.id),
        "url": getattr(w, "url", ""),
        "events": list(getattr(w, "events", []) or []),
        "active": getattr(w, "active", True),
        "description": getattr(w, "description", None),
    }


def _delivery_to_dict(d) -> dict:
    return {
        "delivered_at": str(getattr(d, "delivered_at", "") or ""),
        "status": getattr(d, "status", None),
        "event_type": getattr(d, "event_type", None),
        "attempt_count": getattr(d, "attempt_count", 1),
    }
