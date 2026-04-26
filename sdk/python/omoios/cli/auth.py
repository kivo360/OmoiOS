"""`omoios auth github` — GitHub device-code OAuth flow.

GitHub's device flow is the right shape for a CLI: no localhost
redirect, no client secret, just a user_code the user types into a
browser while we poll the token endpoint. See
https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps#device-flow.

Resulting token is written to the XDG config file as `github_token`
so future commands can use it without re-prompting. The token is
local-only for now — there's no backend route that registers a
device-flow token against an OmoiOS user yet (the web redirect path
covers account linking).
"""

from __future__ import annotations

import time
import webbrowser
from typing import Annotated, Any

import httpx
from cyclopts import App, Parameter
from rich.panel import Panel

from omoios.cli._config import update_config
from omoios.cli._ui import CliError, console, ok


# OmoiOS production GitHub OAuth App. Device Flow is enabled on this
# app (verified 2026-04-26 — request returns a device_code); the local
# dev app `Ov23lin1294IImhbsPHk` has Device Flow disabled, so we use
# the production client_id by default and let users override via
# `OMOIOS_GITHUB_CLIENT_ID`.
DEFAULT_CLIENT_ID = "Ov23lix7wDPhUskntl4c"

DEVICE_CODE_URL = "https://github.com/login/device/code"
TOKEN_URL = "https://github.com/login/oauth/access_token"
DEFAULT_SCOPES = "read:user user:email repo read:org"


auth_app = App(
    name="auth",
    help="Authenticate against external providers (GitHub, etc.).",
)


@auth_app.command(name="github")
def github_cmd(
    client_id: Annotated[
        str,
        Parameter(
            name="--client-id",
            env_var="OMOIOS_GITHUB_CLIENT_ID",
            help="GitHub OAuth App client_id with Device Flow enabled.",
        ),
    ] = DEFAULT_CLIENT_ID,
    scopes: Annotated[
        str,
        Parameter(name="--scopes", help="Space-separated GitHub OAuth scopes."),
    ] = DEFAULT_SCOPES,
    no_browser: Annotated[
        bool,
        Parameter(
            name="--no-browser",
            help="Skip auto-opening the verification URL in a browser.",
        ),
    ] = False,
) -> None:
    """Authenticate to GitHub via the device-code flow.

    Prints a short user_code, opens GitHub's verification page, polls
    until the user authorizes, then writes the access token to the
    XDG config file.
    """
    device = _request_device_code(client_id, scopes)

    user_code = device["user_code"]
    verification_uri = device["verification_uri"]
    console.print(
        Panel.fit(
            f"Visit [link={verification_uri}]{verification_uri}[/link]\n"
            f"Enter code: [bold yellow]{user_code}[/bold yellow]",
            title="GitHub Device Authorization",
            border_style="cyan",
        )
    )

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
    ok(f"GitHub token saved to [dim]{path}[/dim]")
    if granted:
        console.print(f"  scopes: [dim]{granted}[/dim]")


def _request_device_code(client_id: str, scopes: str) -> dict[str, Any]:
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            DEVICE_CODE_URL,
            data={"client_id": client_id, "scope": scopes},
            headers={"Accept": "application/json"},
        )
    if resp.status_code != 200:
        raise CliError(
            f"GitHub device-code request failed: {resp.status_code} "
            f"{resp.text[:200]}"
        )
    data = resp.json()
    if "device_code" not in data:
        raise CliError(
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
                raise CliError(
                    f"GitHub device-code authorization failed: {err}"
                )
            if err:
                raise CliError(f"GitHub error: {err}")

    raise CliError(
        "Timed out waiting for GitHub authorization (the user_code expired)."
    )


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
    console.print(
        Panel.fit(
            f"Visit [link={device['verification_uri']}]{device['verification_uri']}[/link]\n"
            f"Enter code: [bold yellow]{device['user_code']}[/bold yellow]",
            title="GitHub Device Authorization",
            border_style="cyan",
        )
    )
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
