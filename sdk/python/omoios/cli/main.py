"""`omoios` command — Click root + global options.

Subcommand groups:
  - `omoios providers` — credential bindings (list/add/delete)
  - `omoios auth`      — GitHub device-code flow (placeholder; lands next)
  - `omoios signup`    — tenant onboarding (placeholder; lands next)

Each subcommand resolves its CliConfig via `_config.resolve_config()` so
the auth precedence is uniform: CLI flag > env var > XDG config file.
"""

from __future__ import annotations

import click

from omoios.cli import auth as _auth
from omoios.cli import providers as _providers
from omoios.cli import signup as _signup


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(package_name="omoios-sdk", prog_name="omoios")
@click.option(
    "--api-base-url",
    envvar="OMOIOS_API_BASE_URL",
    help="Override the API base URL (precedence: flag > env > config).",
)
@click.option(
    "--api-key",
    envvar="OMOIOS_PLATFORM_API_KEY",
    help="Override the platform API key (precedence: flag > env > config).",
)
@click.pass_context
def cli(ctx: click.Context, api_base_url: str | None, api_key: str | None) -> None:
    """Terminal-first OmoiOS CLI.

    Standing rule: every product capability lands here before any UI
    exists for it. Provider management, GitHub auth, tenant onboarding —
    all driven from `omoios <subcommand>`.
    """
    ctx.ensure_object(dict)
    ctx.obj["api_base_url"] = api_base_url
    ctx.obj["api_key"] = api_key


cli.add_command(_providers.providers)
cli.add_command(_auth.auth)
cli.add_command(_signup.signup)


def main() -> None:
    """Console-script entry point declared in pyproject.toml."""
    cli(obj={})


if __name__ == "__main__":
    main()
