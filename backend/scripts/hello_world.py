#!/usr/bin/env python3
"""Hello World script with ASCII art for OmoiOS.

A simple demonstration script that displays a greeting message
with ASCII art styling.
"""

import sys


def get_ascii_art():
    """Return the ASCII art banner."""
    return r"""
    _   _      _ _        __        __         _     _ _
   | | | | ___| | | ___   \ \      / /__  _ __| | __| | |
   | |_| |/ _ \ | |/ _ \   \ \ /\ / / _ \| '__| |/ _` | |
   |  _  |  __/ | | (_) |   \ V  V / (_) | |  | | (_| |_|
   |_| |_|\___|_|_|\___/     \_/\_/ \___/|_|  |_|\__,_(_)

    """


def get_omoi_art():
    """Return OmoiOS ASCII art."""
    return r"""
     ___                  _  ___  ____
    / _ \ _ __ ___   ___ (_)/ _ \/ ___|
   | | | | '_ ` _ \ / _ \| | | | \___ \
   | |_| | | | | | | (_) | | |_| |___) |
    \___/|_| |_| |_|\___/|_|\___/|____/

    """


def main():
    """Main entry point."""
    print("=" * 60)
    print(get_ascii_art())
    print("=" * 60)
    print()
    print("  Welcome to:")
    print(get_omoi_art())
    print("=" * 60)
    print()
    print("  This is a simple hello world demonstration script.")
    print("  OmoiOS - Orchestrating AI agents for software development.")
    print()
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
