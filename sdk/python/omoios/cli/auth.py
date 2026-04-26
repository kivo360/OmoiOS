"""`omoios auth` — placeholder for the GitHub device-code flow.

The real implementation will land next session per the queue in
`tasks/next-session-instructions.md` §5: device-code OAuth that polls
GitHub's `/login/device/code` endpoint and writes the resulting token
to the XDG config file (`omoios.cli._config.write_config`). Backend's
existing `services/oauth/github.py:exchange_code` covers the web
redirect path; only the device flow is missing.

Keeping this command registered as a stub now so:
  - `omoios --help` shows the surface-to-be
  - users hit a useful "not implemented yet" message instead of a
    typo-style "no such command" error
"""

from __future__ import annotations

import click


@click.group()
def auth() -> None:
    """Authenticate against external providers (GitHub, etc.)."""


@auth.command("github")
def github_cmd() -> None:
    """Authenticate to GitHub via the device-code flow (planned)."""
    raise click.ClickException(
        "`omoios auth github` is not implemented yet. The device-code "
        "flow ships next per tasks/next-session-instructions.md §5. For "
        "now use the web redirect flow at "
        "`backend/omoi_os/services/oauth/github.py:exchange_code`."
    )
