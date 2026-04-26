"""Rich-powered output helpers shared across `omoios` subcommands.

Centralizes the Console instances and the standard ✓ / · / Error glyphs
so the look-and-feel stays consistent. Anything that wants to print
status to the user should go through these helpers rather than calling
``print`` or ``rich.print`` directly.
"""

from __future__ import annotations

import sys
from typing import NoReturn

from rich.console import Console

# stdout and stderr consoles. We pin `soft_wrap=True` so JSON output
# (which is the contract for `--json` flags) doesn't get wrapped at
# terminal width and break downstream tooling.
console = Console(soft_wrap=True)
err_console = Console(stderr=True, soft_wrap=True)


def ok(message: str) -> None:
    """Print a success line, e.g. `✓ created binding cred-9 (fw)`."""
    console.print(f"[green]✓[/green] {message}")


def info(message: str) -> None:
    """Print a non-status diagnostic line — slightly muted."""
    console.print(f"[dim]·[/dim] {message}")


def die(message: str, *, code: int = 1) -> NoReturn:
    """Print an error and exit. Always writes to stderr so JSON
    contracts on stdout aren't polluted."""
    err_console.print(f"[bold red]Error:[/bold red] {message}")
    sys.exit(code)


class CliError(Exception):
    """Raise this from helper functions instead of calling sys.exit
    directly when you want the caller to decide whether to abort.
    The top-level command handler converts it via :func:`die`."""

    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
