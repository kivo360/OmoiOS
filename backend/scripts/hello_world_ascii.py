#!/usr/bin/env python3
"""Hello World script with ASCII art.

A simple demonstration script that displays a Hello World message
with decorative ASCII art.

Usage:
    uv run python scripts/hello_world_ascii.py
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text


ASCII_ART = r"""
  _   _      _ _        __        __         _     _ _
 | | | | ___| | | ___   \ \      / /__  _ __| | __| | |
 | |_| |/ _ \ | |/ _ \   \ \ /\ / / _ \| '__| |/ _` | |
 |  _  |  __/ | | (_) |   \ V  V / (_) | |  | | (_| |_|
 |_| |_|\___|_|_|\___/     \_/\_/ \___/|_|  |_|\__,_(_)
"""


def main() -> None:
    """Display Hello World with ASCII art."""
    console = Console()

    # Create styled ASCII art text
    art_text = Text(ASCII_ART, style="bold cyan")

    # Display in a decorative panel
    panel = Panel(
        art_text,
        title="[bold magenta]OmoiOS[/bold magenta]",
        subtitle="[dim]Hello from the spec-driven agent system[/dim]",
        border_style="bright_blue",
    )

    console.print()
    console.print(panel)
    console.print()
    console.print("[green]Welcome to OmoiOS![/green] :wave:", justify="center")
    console.print()


if __name__ == "__main__":
    main()
