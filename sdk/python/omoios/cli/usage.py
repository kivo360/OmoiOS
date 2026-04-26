"""`omoios usage` — current-period usage and per-session breakdown.

Powers spec §18 #6 (usage-based billing) at the CLI level. The SDK
exposes `usage.current(...)` and `usage.for_session(...)` — both
return JSON-shaped dicts so we just pretty-print them.
"""

from __future__ import annotations

import json as _json
from typing import Annotated, Optional

from cyclopts import App, Parameter

from omoios.cli._config import resolve_config
from omoios.cli._sdk import run_sdk
from omoios.cli._ui import console


usage_app = App(
    name="usage",
    help="Inspect platform usage for the current period or a single session.",
)


@usage_app.command(name="current")
def current_cmd(
    period: Annotated[
        Optional[str],
        Parameter(
            name="--period",
            help="Period to query (e.g. 'month', 'day', or backend-defined).",
        ),
    ] = None,
    json_output: Annotated[bool, Parameter(name="--json")] = True,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Print current-period usage as JSON.

    Default is JSON because usage payloads vary by backend; consumers
    that need a fixed shape pipe through jq.
    """
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    body = run_sdk(_current(cfg.api_base_url, cfg.api_key, period))
    if json_output:
        console.print_json(_json.dumps(body))
        return
    # Fallback flat-print for the rare --no-json caller.
    for k, v in body.items():
        console.print(f"  [dim]{k}:[/dim] {v}")


@usage_app.command(name="for-session")
def for_session_cmd(
    session_id: Annotated[str, Parameter(help="Session ID.")],
    json_output: Annotated[bool, Parameter(name="--json")] = True,
    api_base_url: Annotated[
        Optional[str], Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL")
    ] = None,
    api_key: Annotated[
        Optional[str], Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY")
    ] = None,
) -> None:
    """Print usage attributable to one session as JSON."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)
    body = run_sdk(_for_session(cfg.api_base_url, cfg.api_key, session_id))
    if json_output:
        console.print_json(_json.dumps(body))
        return
    for k, v in body.items():
        console.print(f"  [dim]{k}:[/dim] {v}")


# ─── async impls ─────────────────────────────────────────────────────────────


async def _current(api_base_url, api_key, period):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        kwargs = {"period": period} if period else {}
        return await client.usage.current(**kwargs)


async def _for_session(api_base_url, api_key, session_id):
    from omoios import AsyncOmoiOSClient

    async with AsyncOmoiOSClient(
        base_url=api_base_url, api_key=api_key, timeout=30.0
    ) as client:
        return await client.usage.for_session(session_id)
