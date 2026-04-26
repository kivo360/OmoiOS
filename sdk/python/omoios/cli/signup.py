"""`omoios signup` — interactive tenant onboarding.

Wraps the same backend calls as `scripts/setup_local_smoke_account.py`
but driven from the user's terminal:

  1. POST /api/v1/auth/register   → user
  2. POST /api/v1/auth/login      → JWT
  3. POST /api/v1/organizations   → org (if user has none yet)
  4. POST /api/v1/auth/api-keys   → platform API key
  5. write XDG config             → so future `omoios *` commands
                                    don't need env vars
  6. (optional) chain into `omoios auth github`
"""

from __future__ import annotations

from typing import Optional

import click
import httpx

from omoios.cli._config import CliConfig, write_config


@click.command("signup")
@click.option(
    "--api-base-url",
    envvar="OMOIOS_API_BASE_URL",
    required=True,
    help="Base URL of the OmoiOS API (e.g. https://api.omoios.dev).",
)
@click.option(
    "--email",
    prompt="Email",
    help="Account email (will be the login identity).",
)
@click.option(
    "--password",
    prompt="Password",
    hide_input=True,
    confirmation_prompt=True,
    help="Account password (will be hidden during entry).",
)
@click.option(
    "--full-name",
    default="",
    help="Display name for the new account (optional).",
)
@click.option(
    "--org-name",
    default=None,
    help="Name for the org to create. Defaults to '<email>'s Org'.",
)
@click.option(
    "--key-name",
    default="omoios-cli",
    show_default=True,
    help="Friendly name for the minted API key.",
)
@click.option(
    "--connect-github/--no-connect-github",
    default=False,
    help="After signup, run `omoios auth github` to link a GitHub token.",
)
def signup(
    api_base_url: str,
    email: str,
    password: str,
    full_name: str,
    org_name: Optional[str],
    key_name: str,
    connect_github: bool,
) -> None:
    """Register a new OmoiOS tenant and persist credentials locally."""
    api = api_base_url.rstrip("/")

    with httpx.Client(base_url=api, timeout=15.0) as client:
        _register(client, email=email, password=password, full_name=full_name)
        click.echo(f"✓ registered {email}")

        jwt = _login(client, email=email, password=password)
        click.echo("✓ logged in")

        org_id = _ensure_org(
            client, jwt=jwt, name=org_name or f"{email}'s Org"
        )
        click.echo(f"✓ org {org_id}")

        api_key, user_id = _mint_api_key(
            client, jwt=jwt, org_id=org_id, name=key_name
        )
        click.echo(f"✓ minted api key (name={key_name})")

    cfg = CliConfig(
        api_base_url=api,
        api_key=api_key,
        user_id=user_id,
    )
    path = write_config(cfg)
    click.echo(f"✓ config written to {path}")

    if connect_github:
        # Local import dodges a circular import at decorator load.
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
    # Treat "already registered" as a soft-success — signup is idempotent
    # for the local-smoke flow this command absorbs.
    if resp.status_code == 409 or "already" in resp.text.lower():
        click.echo(f"· user {email} already exists, continuing")
        return
    raise click.ClickException(
        f"register failed: {resp.status_code} {resp.text[:300]}"
    )


def _login(client: httpx.Client, *, email: str, password: str) -> str:
    resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    if resp.status_code != 200:
        raise click.ClickException(
            f"login failed: {resp.status_code} {resp.text[:300]}"
        )
    body = resp.json()
    token = body.get("access_token")
    if not token:
        raise click.ClickException(f"login response missing access_token: {body}")
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
            # Reuse the first org silently — fresh signups will have none,
            # so this only matters when the email already existed.
            return items[0]["id"]

    import time as _time
    slug = name.lower().replace(" ", "-").replace("'", "") + f"-{int(_time.time())}"
    resp = client.post(
        "/api/v1/organizations",
        headers=headers,
        json={"name": name, "slug": slug},
    )
    if resp.status_code not in (200, 201):
        raise click.ClickException(
            f"org create failed: {resp.status_code} {resp.text[:300]}"
        )
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
        raise click.ClickException(
            f"api-key mint failed: {resp.status_code} {resp.text[:300]}"
        )
    body = resp.json()
    return body["key"], body.get("user_id")
