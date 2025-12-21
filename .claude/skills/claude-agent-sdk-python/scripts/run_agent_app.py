#!/usr/bin/env python3
"""
Run a Claude Agent SDK application independently for testing.

Usage:
    python run_agent_app.py path/to/app.py [options]
    python run_agent_app.py path/to/app.py --prompt "Your prompt here"
    python run_agent_app.py path/to/app.py --cwd /project --max-turns 5
"""

import argparse
import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any


def load_module(path: Path):
    """Dynamically load a Python module from path."""
    spec = importlib.util.spec_from_file_location("agent_app", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["agent_app"] = module
    spec.loader.exec_module(module)
    return module


def find_entry_point(module) -> Any:
    """Find the main entry point in the module."""
    # Look for common patterns
    for name in ["main", "run", "agent_main", "run_agent"]:
        if hasattr(module, name):
            return getattr(module, name)

    # Look for async functions
    for name, obj in vars(module).items():
        if asyncio.iscoroutinefunction(obj) and not name.startswith("_"):
            return obj

    return None


async def run_app(app_path: Path, args: argparse.Namespace):
    """Run the agent application."""
    print(f"Loading agent app from: {app_path}")

    module = load_module(app_path)
    entry_point = find_entry_point(module)

    if entry_point is None:
        print("Error: No entry point found (main, run, or async function)")
        sys.exit(1)

    print(f"Found entry point: {entry_point.__name__}")

    # Check if it accepts arguments
    import inspect
    sig = inspect.signature(entry_point)

    if len(sig.parameters) > 0:
        # Pass configuration as kwargs if accepted
        kwargs = {}
        if "prompt" in sig.parameters and args.prompt:
            kwargs["prompt"] = args.prompt
        if "cwd" in sig.parameters and args.cwd:
            kwargs["cwd"] = args.cwd
        if "max_turns" in sig.parameters and args.max_turns:
            kwargs["max_turns"] = args.max_turns

        if asyncio.iscoroutinefunction(entry_point):
            await entry_point(**kwargs) if kwargs else await entry_point()
        else:
            entry_point(**kwargs) if kwargs else entry_point()
    else:
        if asyncio.iscoroutinefunction(entry_point):
            await entry_point()
        else:
            entry_point()


def main():
    parser = argparse.ArgumentParser(
        description="Run a Claude Agent SDK application for testing"
    )
    parser.add_argument(
        "app_path",
        type=Path,
        help="Path to the agent application Python file"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Override the prompt to send to the agent"
    )
    parser.add_argument(
        "--cwd",
        type=Path,
        help="Working directory for the agent"
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        help="Maximum conversation turns"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if not args.app_path.exists():
        print(f"Error: File not found: {args.app_path}")
        sys.exit(1)

    if args.verbose:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    try:
        asyncio.run(run_app(args.app_path, args))
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
