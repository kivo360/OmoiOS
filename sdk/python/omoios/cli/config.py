"""`omoios config` — inspect and manage the local CLI config file.

The config is a small JSON blob written by `omoios signup` (and
amended by `omoios auth github`) at the path resolved by
:func:`omoios.cli._config.config_path`. These commands are the only
sanctioned way for users to peek at it; please do not encourage
hand-editing.
"""

from __future__ import annotations

import json as _json
from typing import Annotated

from cyclopts import App, Parameter
from rich.prompt import Confirm

from omoios.cli._config import config_path
from omoios.cli._ui import CliError, console, info, ok


config_app = App(
    name="config",
    help="Inspect and manage the local OmoiOS config file.",
)


@config_app.command(name="path")
def path_cmd() -> None:
    """Print the canonical config-file path (whether or not it exists)."""
    console.print(str(config_path()))


@config_app.command(name="show")
def show_cmd(
    reveal: Annotated[
        bool,
        Parameter(
            name="--reveal",
            help="Print full secret values instead of masking them.",
        ),
    ] = False,
) -> None:
    """Pretty-print the current config (api_key + github_token are
    masked unless --reveal is passed)."""
    path = config_path()
    if not path.exists():
        info(
            f"no config at [dim]{path}[/dim] — run `omoios signup` to create one."
        )
        return
    try:
        data = _json.loads(path.read_text())
    except _json.JSONDecodeError as exc:
        raise CliError(f"config at {path} is not valid JSON: {exc}") from exc

    if not reveal:
        for secret_key in ("api_key", "user_jwt", "github_token"):
            if val := data.get(secret_key):
                data[secret_key] = (
                    f"{val[:14]}…(redacted, --reveal to show)"
                    if len(val) > 14
                    else "…(redacted)"
                )
    console.print_json(_json.dumps(data))


@config_app.command(name="clear")
def clear_cmd(
    yes: Annotated[
        bool,
        Parameter(name=["--yes", "-y"], help="Skip the confirmation prompt."),
    ] = False,
) -> None:
    """Delete the local config file (you'll need to re-run `omoios signup`)."""
    path = config_path()
    if not path.exists():
        info(f"no config at [dim]{path}[/dim] — nothing to clear.")
        return

    if not yes:
        confirmed = Confirm.ask(
            f"Delete [bold]{path}[/bold]?", default=False
        )
        if not confirmed:
            console.print("[yellow]Aborted.[/yellow]")
            raise CliError("aborted by user")

    path.unlink()
    ok(f"removed [dim]{path}[/dim]")
