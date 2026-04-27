"""`omoios signup` — interactive tenant onboarding.

Wraps the same backend calls as `scripts/setup_local_smoke_account.py`
but driven from the user's terminal:

  1. POST /api/v1/auth/register   → user
  2. POST /api/v1/auth/login      → JWT
  3. POST /api/v1/organizations   → org (if user has none yet)
  4. POST /api/v1/auth/api-keys   → platform API key
  5. write XDG config
  6. (optional) chain into `omoios auth github`
"""

from __future__ import annotations

import time
from typing import Annotated, Optional

import httpx
from cyclopts import Parameter
from rich.prompt import Prompt

from omoios.cli._config import CliConfig, write_config
from omoios.cli._ui import CliError, console, info, ok


def signup(
    api_base_url: Annotated[
        str,
        Parameter(
            name="--api-base-url",
            env_var="OMOIOS_API_BASE_URL",
            help="Base URL of the OmoiOS API (e.g. https://api.omoios.dev).",
        ),
    ],
    email: Annotated[
        Optional[str],
        Parameter(name="--email", help="Account email (login identity)."),
    ] = None,
    password: Annotated[
        Optional[str],
        Parameter(
            name="--password",
            help="Account password. If omitted, prompted (hidden).",
        ),
    ] = None,
    full_name: Annotated[
        str,
        Parameter(name="--full-name", help="Display name for the new account."),
    ] = "",
    org_name: Annotated[
        Optional[str],
        Parameter(
            name="--org-name",
            help="Name for the org. Defaults to '<email>'s Org'.",
        ),
    ] = None,
    key_name: Annotated[
        str,
        Parameter(name="--key-name", help="Friendly name for the minted API key."),
    ] = "omoios-cli",
    connect_github: Annotated[
        bool,
        Parameter(
            name="--connect-github",
            help="After signup, run `omoios auth github` to link a GitHub token.",
        ),
    ] = False,
) -> None:
    """Register a new OmoiOS tenant and persist credentials locally."""
    api = api_base_url.rstrip("/")

    if not email:
        email = Prompt.ask("Email")
    if not password:
        password = Prompt.ask("Password", password=True)
        confirm = Prompt.ask("Repeat for confirmation", password=True)
        if password != confirm:
            raise CliError("passwords did not match")

    with httpx.Client(base_url=api, timeout=15.0) as client:
        _register(client, email=email, password=password, full_name=full_name)
        ok(f"registered [bold]{email}[/bold]")

        jwt = _login(client, email=email, password=password)
        ok("logged in")

        org_id = _ensure_org(
            client, jwt=jwt, name=org_name or f"{email}'s Org"
        )
        ok(f"org [bold]{org_id}[/bold]")

        api_key, user_id = _mint_api_key(
            client, jwt=jwt, org_id=org_id, name=key_name
        )
        ok(f"minted api key (name=[cyan]{key_name}[/cyan])")

    cfg = CliConfig(
        api_base_url=api,
        api_key=api_key,
        user_id=user_id,
        user_jwt=jwt,
    )
    path = write_config(cfg)
    ok(f"config written to [dim]{path}[/dim]")
    info(
        "stored user JWT for WebSocket routes (e.g. `omoios sessions connect`); "
        "rerun signup or `omoios auth refresh` if it expires."
    )

    if connect_github:
        # Local import dodges a circular import at module load.
        from omoios.cli.auth import run_github_device_flow

        run_github_device_flow()


# ─── HTTP helpers ────────────────────────────────────────────────────────────


def _register(
    client: httpx.Client, *, email: str, password: str, full_name: str
) -> None:
    payload = {"email": email, "password": password}
    if full_name:
        payload["full_name"] = full_name
    resp = client.post("/api/v1/auth/register", json=payload)
    if resp.status_code in (200, 201):
        return
    if resp.status_code == 409 or "already" in resp.text.lower():
        info(f"user [bold]{email}[/bold] already exists, continuing")
        return
    raise CliError(f"register failed: {resp.status_code} {resp.text[:300]}")


def _login(client: httpx.Client, *, email: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    if resp.status_code != 200:
        raise CliError(f"login failed: {resp.status_code} {resp.text[:300]}")
    body = resp.json()
    token = body.get("access_token")
    if not token:
        raise CliError(f"login response missing access_token: {body}")
    return token


def _ensure_org(client: httpx.Client, *, jwt: str, name: str) -> str:
    headers = {"Authorization": f"Bearer {jwt}"}
    resp = client.get("/api/v1/organizations", headers=headers)
    if resp.status_code == 200:
        items = resp.json()
        if isinstance(items, dict):
            items = items.get("items", [])
        for org in items:
            if org.get("name") == name:
                return org["id"]
        if items:
            return items[0]["id"]

    slug = name.lower().replace(" ", "-").replace("'", "") + f"-{int(time.time())}"
    resp = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": name, "slug": slug},
    )
    if resp.status_code not in (200, 201):
        raise CliError(f"org create failed: {resp.status_code} {resp.text[:300]}")
    return resp.json()["id"]


def _mint_api_key(
    client: httpx.Client, *, jwt: str, org_id: str, name: str
) -> tuple[str, Optional[str]]:
    resp = client.post(
        "/api/v1/auth/api-keys",
        headers={"Authorization": f"Bearer {jwt}"},
        json={"name": name, "scopes": ["*"], "organization_id": org_id},
    )
    if resp.status_code not in (200, 201):
        raise CliError(f"api-key mint failed: {resp.status_code} {resp.text[:300]}")
    body = resp.json()
    return body["key"], body.get("user_id")
