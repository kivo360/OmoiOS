"""`omoios auth github` — GitHub device-code OAuth flow.

GitHub's device flow is the right shape for a CLI: no localhost
redirect, no client secret, just a user_code the user types into a
browser while we poll the token endpoint. See
https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow.

The OAuth App used for the existing web redirect (`AUTH_GITHUB_CLIENT_ID`
in backend/.env) must have "Device Flow" enabled in its GitHub app
settings. Override the client_id at the CLI seam via
`OMOIOS_GITHUB_CLIENT_ID` if you want to use a separate CLI app.

Resulting token is written to the XDG config file as `github_token` so
future commands can use it without re-prompting. The token is local-only
for now — there's no backend route that registers a device-flow token
against an OmoiOS user yet (the web redirect path covers account
linking).
"""

from __future__ import annotations

import time
import webbrowser
from typing import Any

import click
import httpx

from omoios.cli._config import update_config

# The OmoiOS production GitHub OAuth App. Device Flow is enabled on
# this app (verified 2026-04-26 — request returns a device_code);
# the local-dev app `Ov23lin1294IImhbsPHk` has Device Flow disabled,
# so we use the production client_id by default and let users override
# via `OMOIOS_GITHUB_CLIENT_ID`.
DEFAULT_CLIENT_ID = "Ov23lix7wDPhUskntl4c"

DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
DEFAULT_SCOPES = "read:user user:email repo read:org"


@click.group()
def auth() -> None:
    """Authenticate against external providers (GitHub, etc.)."""


@auth.command("github")
@click.option(
    "--client-id",
    envvar="OMOIOS_GITHUB_CLIENT_ID",
    default=DEFAULT_CLIENT_ID,
    show_default=True,
    help="GitHub OAuth App client_id with Device Flow enabled.",
)
@click.option(
    "--scopes",
    default=DEFAULT_SCOPES,
    show_default=True,
    help="Space-separated GitHub OAuth scopes to request.",
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Skip auto-opening the verification URL in a browser.",
)
def github_cmd(client_id: str, scopes: str, no_browser: bool) -> None:
    """Authenticate to GitHub via the device-code flow.

    Prints a short user_code, opens GitHub's verification page, polls
    until the user authorizes, then writes the access token to the
    XDG config file.
    """
    device = _request_device_code(client_id, scopes)

    user_code = device["user_code"]
    verification_uri = device["verification_uri"]
    click.echo(f"\nGo to: {verification_uri}")
    click.echo(f"Enter code: \033[1m{user_code}\033[0m\n")

    if not no_browser:
        try:
            webbrowser.open(verification_uri)
        except Exception:  # noqa: BLE001 — browser is best-effort
            pass

    token_payload = _poll_for_token(
        client_id,
        device_code=device["device_code"],
        interval=int(device.get("interval", 5)),
        expires_in=int(device.get("expires_in", 900)),
    )

    access_token = token_payload["access_token"]
    granted = token_payload.get("scope", "")
    path = update_config(github_token=access_token)
    click.echo(f"✓ GitHub token saved to {path}")
    if granted:
        click.echo(f"  scopes: {granted}")


def _request_device_code(client_id: str, scopes: str) -> dict[str, Any]:
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            DEVICE_CODE_URL,
            data={"client_id": client_id, "scope": scopes},
            headers={"Accept": "application/json"},
        )
    if resp.status_code != 200:
        raise click.ClickException(
            f"GitHub device-code request failed: {resp.status_code} "
            f"{resp.text[:200]}"
        )
    data = resp.json()
    if "device_code" not in data:
        raise click.ClickException(
            "GitHub did not return a device_code. The OAuth App may not "
            "have Device Flow enabled. Set OMOIOS_GITHUB_CLIENT_ID to a "
            f"client_id with Device Flow turned on. Response: {data}"
        )
    return data


def _poll_for_token(
    client_id: str,
    *,
    device_code: str,
    interval: int,
    expires_in: int,
) -> dict[str, Any]:
    deadline = time.monotonic() + expires_in
    poll = max(interval, 1)

    with httpx.Client(timeout=15.0) as client:
        while time.monotonic() < deadline:
            time.sleep(poll)
            resp = client.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "device_code": device_code,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                },
                headers={"Accept": "application/json"},
            )
            data: dict[str, Any] = resp.json() if resp.content else {}

            if "access_token" in data:
                return data

            err = data.get("error")
            if err == "authorization_pending":
                continue
            if err == "slow_down":
                poll += 5
                continue
            if err in ("expired_token", "access_denied"):
                raise click.ClickException(
                    f"GitHub device-code authorization failed: {err}"
                )
            if err:
                raise click.ClickException(f"GitHub error: {err}")

    raise click.ClickException(
        "Timed out waiting for GitHub authorization (the user_code expired)."
    )


# Re-export for `omoios signup` to chain into without circular imports
# at the click-decorator level.
def run_github_device_flow(
    *,
    client_id: str = DEFAULT_CLIENT_ID,
    scopes: str = DEFAULT_SCOPES,
    open_browser: bool = True,
) -> str:
    """Programmatic entry — used by `omoios signup` to chain GitHub
    auth after writing the platform config. Returns the access token
    and writes it to the XDG config."""
    device = _request_device_code(client_id, scopes)
    click.echo(f"\nGo to: {device['verification_uri']}")
    click.echo(f"Enter code: \033[1m{device['user_code']}\033[0m\n")
    if open_browser:
        try:
            webbrowser.open(device["verification_uri"])
        except Exception:  # noqa: BLE001
            pass
    token_payload = _poll_for_token(
        client_id,
        device_code=device["device_code"],
        interval=int(device.get("interval", 5)),
        expires_in=int(device.get("expires_in", 900)),
    )
    token = token_payload["access_token"]
    update_config(github_token=token)
    return token
