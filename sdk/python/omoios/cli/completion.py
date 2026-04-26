"""`omoios completion` — shell completion management.

Two modes (per the design call): eval-friendly + file-install. Cyclopts
ships the actual completion-script generation; this module is just the
user-facing CLI wrapper that exposes both shapes.

  - `omoios completion show [SHELL]` — print the script to stdout
    (for `eval "$(omoios completion show zsh)"` in dotfiles).
  - `omoios completion install [SHELL]` — write the completion script
    to the shell's standard location and append a source line to the
    matching RC file. Uses cyclopts' built-in `install_completion`.

Both auto-detect `$SHELL` when the argument is omitted.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from cyclopts import App, Parameter

from omoios.cli._ui import CliError, console, ok


completion_app = App(
    name="completion",
    help="Generate or install shell completion (zsh / bash / fish).",
)


@completion_app.command(name="show")
def show_cmd(
    shell: Annotated[
        Optional[Literal["zsh", "bash", "fish"]],
        Parameter(help="Target shell. Auto-detected from $SHELL if omitted."),
    ] = None,
) -> None:
    """Print the completion script to stdout (eval-friendly)."""
    # Lazy import to avoid circulating with `omoios.cli.main`.
    from omoios.cli.main import app

    try:
        script = app.generate_completion(shell=shell, prog_name="omoios")
    except Exception as exc:  # noqa: BLE001 — translate cyclopts' own errors
        raise CliError(f"could not generate completion: {exc}") from exc

    # `console.print` would Rich-format; we want raw shell so it's eval-able.
    print(script)


@completion_app.command(name="install")
def install_cmd(
    shell: Annotated[
        Optional[Literal["zsh", "bash", "fish"]],
        Parameter(help="Target shell. Auto-detected from $SHELL if omitted."),
    ] = None,
    output: Annotated[
        Optional[str],
        Parameter(
            name=["--output", "-o"],
            help=(
                "Override the install location. Defaults to the shell's "
                "standard completion path."
            ),
        ),
    ] = None,
    no_startup: Annotated[
        bool,
        Parameter(
            name="--no-startup",
            help="Skip appending a source line to the shell RC file.",
        ),
    ] = False,
) -> None:
    """Install the completion script to the shell's standard location."""
    from pathlib import Path

    from omoios.cli.main import app

    try:
        path = app.install_completion(
            shell=shell,
            output=Path(output) if output else None,
            add_to_startup=not no_startup,
        )
    except Exception as exc:  # noqa: BLE001
        raise CliError(f"could not install completion: {exc}") from exc

    ok(f"installed completion → [dim]{path}[/dim]")
    if not no_startup:
        console.print(
            "  [dim]source line appended to your shell rc; restart the "
            "shell or `source` it to activate.[/dim]"
        )
