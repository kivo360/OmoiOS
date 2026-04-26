"""`omoios whoami` — print the user/org bound to the current API key.

Useful as a smoke check after `omoios signup` or when debugging an
"is my key still good?" situation. Talks to `GET /api/v1/auth/me`.
"""

from __future__ import annotations

import json as _json
from typing import Annotated, Optional

import httpx
from cyclopts import Parameter

from omoios.cli._config import resolve_config
from omoios.cli._ui import CliError, console


def whoami(
    json_output: Annotated[
        bool,
        Parameter(name="--json", help="Emit the raw `/auth/me` JSON payload."),
    ] = False,
    api_base_url: Annotated[
        Optional[str],
        Parameter(name="--api-base-url", env_var="OMOIOS_API_BASE_URL"),
    ] = None,
    api_key: Annotated[
        Optional[str],
        Parameter(name="--api-key", env_var="OMOIOS_PLATFORM_API_KEY"),
    ] = None,
) -> None:
    """Verify the current API key by hitting `/api/v1/auth/me`."""
    cfg = resolve_config(api_base_url=api_base_url, api_key=api_key)

    with httpx.Client(timeout=10.0) as client:
        resp = client.get(
            f"{cfg.api_base_url}/api/v1/auth/me",
            headers={"Authorization": f"Bearer {cfg.api_key}"},
        )
    if resp.status_code == 401:
        raise CliError(
            "401 from /auth/me — the API key is no longer valid. "
            "Run `omoios signup` to mint a fresh one."
        )
    if resp.status_code != 200:
        raise CliError(
            f"/auth/me returned {resp.status_code}: {resp.text[:200]}"
        )

    body = resp.json()
    if json_output:
        console.print_json(_json.dumps(body))
        return

    user_id = body.get("id") or body.get("user_id") or "?"
    email = body.get("email", "?")
    full_name = body.get("full_name") or body.get("name") or ""
    org = body.get("organization") or {}
    org_label = (
        f"{org.get('name', '?')} ({org.get('id', '?')[:8]}…)"
        if org else
        "(no org)"
    )

    console.print(f"[bold]{email}[/bold] {full_name and f'· {full_name}'}")
    console.print(f"  user: [dim]{user_id}[/dim]")
    console.print(f"  org:  [dim]{org_label}[/dim]")
    console.print(f"  api:  [dim]{cfg.api_base_url}[/dim]")
