"""`omoios` command — Cyclopts root + nested subcommand apps.

Subcommand apps:
  - `omoios providers` — credential bindings (list/add/delete)
  - `omoios auth`      — GitHub device-code flow
  - `omoios signup`    — interactive tenant onboarding

Each subcommand resolves its CliConfig via `_config.resolve_config()`
so the auth precedence is uniform: CLI flag > env var > XDG config file.
"""

from __future__ import annotations

import sys

from cyclopts import App

from omoios.cli._ui import CliError, die
from omoios.cli.auth import auth_app
from omoios.cli.providers import providers_app
from omoios.cli.signup import signup

app = App(
    name="omoios",
    version="0.2.0",
    help=(
        "Terminal-first OmoiOS CLI.\n\n"
        "Standing rule: every product capability lands here before any UI "
        "exists for it. Provider management, GitHub auth, tenant onboarding — "
        "all driven from `omoios <subcommand>`."
    ),
)

app.command(providers_app)
app.command(auth_app)
app.command(signup)


def main() -> None:
    """Console-script entry point declared in pyproject.toml.

    We catch :class:`CliError` so helpers can raise without each command
    site reaching for `sys.exit`. Cyclopts handles its own
    parse/argument errors before this layer.
    """
    try:
        app()
    except CliError as exc:
        die(exc.message, code=exc.code)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
