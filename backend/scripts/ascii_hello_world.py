#!/usr/bin/env python3
"""ASCII Hello World script.

A simple utility script that outputs "Hello World" in ASCII art format.
This demonstrates basic ASCII text rendering capabilities.

Requirements:
- REQ-001: WHEN the script is executed, THE SYSTEM SHALL display "Hello World" in ASCII art
- REQ-002: WHEN no arguments provided, THE SYSTEM SHALL use default ASCII art style
- REQ-003: WHEN --compact flag provided, THE SYSTEM SHALL display a smaller ASCII art version

Usage:
    python ascii_hello_world.py           # Default ASCII art
    python ascii_hello_world.py --compact # Compact version
"""

import argparse
import sys

# ASCII art for "HELLO WORLD" - standard block letters
HELLO_WORLD_ASCII = r"""
 _   _      _ _         __        __         _     _
| | | | ___| | | ___    \ \      / /__  _ __| | __| |
| |_| |/ _ \ | |/ _ \    \ \ /\ / / _ \| '__| |/ _` |
|  _  |  __/ | | (_) |    \ V  V / (_) | |  | | (_| |
|_| |_|\___|_|_|\___/      \_/\_/ \___/|_|  |_|\__,_|
"""

# Compact ASCII art version
HELLO_WORLD_COMPACT = r"""
 _  _     _ _        __    __       _    _
| || |___| | |___   / / /\ \ \___ _(_)__| |
| __ / -_) | / _ \  \ \/  \/ / _ \ '_| / _` |
|_||_\___|_|_\___/   \_/\_/\___/_| |_\__,_|
"""

# Simple banner style
HELLO_WORLD_SIMPLE = r"""
+=====================+
|    HELLO WORLD!     |
+=====================+
"""


def print_ascii_hello_world(style: str = "default") -> None:
    """Print Hello World in ASCII art format.

    Args:
        style: The ASCII art style to use ('default', 'compact', or 'simple')
    """
    if style == "compact":
        print(HELLO_WORLD_COMPACT)
    elif style == "simple":
        print(HELLO_WORLD_SIMPLE)
    else:
        print(HELLO_WORLD_ASCII)


def main() -> int:
    """Main entry point for the ASCII Hello World script.

    Returns:
        Exit code (0 for success)
    """
    parser = argparse.ArgumentParser(
        description="Display 'Hello World' in ASCII art format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python ascii_hello_world.py           # Default block letters
    python ascii_hello_world.py --compact # Compact version
    python ascii_hello_world.py --simple  # Simple banner style
        """,
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Use compact ASCII art style",
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Use simple banner style",
    )

    args = parser.parse_args()

    # Determine style based on arguments
    if args.compact:
        style = "compact"
    elif args.simple:
        style = "simple"
    else:
        style = "default"

    print_ascii_hello_world(style)
    return 0


if __name__ == "__main__":
    sys.exit(main())
