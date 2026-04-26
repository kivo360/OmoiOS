"""`omoios` command — Cyclopts root + nested subcommand apps.

Subcommand apps:
  - `omoios providers` — credential bindings (list/add/delete)
  - `omoios auth`      — GitHub device-code flow
  - `omoios signup`    — interactive tenant onboarding

Each subcommand resolves its CliConfig via `_config.resolve_config()`
so the auth precedence is uniform: CLI flag > env var > XDG config file.

The launcher follows the cookbook's "random tips" pattern
(https://cyclopts.readthedocs.io/en/stable/cookbook/random_tips.html):
a `@app.meta.default` wraps the real dispatch so we can sprinkle a
useful one-liner on stderr after a successful command. Tips are
opt-out via `OMOIOS_NO_TIPS=1` or `--no-tips`, and only fire on
clean exits — failures already print their own message and don't
need extra noise.
"""

from __future__ import annotations

import random
import sys
from typing import Annotated

from cyclopts import App, Parameter

from omoios.cli._ui import CliError, die, err_console
from omoios.cli.auth import auth_app
from omoios.cli.config import config_app
from omoios.cli.providers import providers_app
from omoios.cli.sessions import sessions_app
from omoios.cli.signup import signup
from omoios.cli.whoami import whoami

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
app.command(sessions_app)
app.command(auth_app)
app.command(config_app)
app.command(signup)
app.command(whoami)


# Curated tips — short, actionable, grounded in real usage. Each one
# should solve a real footgun or unlock a real workflow.
TIPS: tuple[str, ...] = (
    "Pipe `omoios providers list --json` into `jq` for scripting.",
    "Set $OMOIOS_PROVIDER_KEY before `omoios providers add` so secrets "
    "stay out of shell history.",
    "Run `omoios signup --connect-github` to chain into the GitHub "
    "device-code flow right after onboarding.",
    "Override the API URL per-call with --api-base-url, or per-shell "
    "with $OMOIOS_API_BASE_URL — flag wins.",
    "Config lives at $XDG_CONFIG_HOME/omoios/config.json (falls back to "
    "~/.config/omoios/config.json).",
    "Quiet these tips with $OMOIOS_NO_TIPS=1 or --no-tips.",
    "Run `omoios whoami` to verify the local API key is still valid.",
    "Inspect or wipe local creds with `omoios config show` / "
    "`omoios config clear`.",
    "`omoios sessions create \"<prompt>\" --watch` opens a chat and streams "
    "events live via SSE.",
    "Stuck waiting? `omoios sessions list --status running` shows what's "
    "still in-flight.",
    "GitHub device flow needs the production OAuth App. Override with "
    "$OMOIOS_GITHUB_CLIENT_ID if you have your own.",
)
TIP_PROBABILITY = 0.30


@app.meta.default
def launcher(
    *tokens: Annotated[str, Parameter(show=False, allow_leading_hyphen=True)],
    no_tips: Annotated[
        bool,
        Parameter(
            name="--no-tips",
            env_var="OMOIOS_NO_TIPS",
            negative="",
            help="Suppress the occasional post-command tip.",
        ),
    ] = False,
) -> None:
    """Dispatch tokens to the real app, optionally trailing a tip.

    Errors raised by subcommands bubble out before the tip block so a
    failed command never gets a tip stapled to it.
    """
    app(tokens)
    if not no_tips and TIPS and random.random() < TIP_PROBABILITY:
        err_console.print(f"\n[dim]💡 tip:[/dim] {random.choice(TIPS)}")


def main() -> None:
    """Console-script entry point declared in pyproject.toml.

    Routes through `app.meta` so the tip launcher is in the call path.
    `CliError` is caught here so helpers can raise without each command
    site reaching for `sys.exit`.
    """
    try:
        app.meta()
    except CliError as exc:
        die(exc.message, code=exc.code)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
