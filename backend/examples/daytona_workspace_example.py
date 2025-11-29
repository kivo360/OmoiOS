#!/usr/bin/env python3
"""Example: Using DaytonaWorkspace for task execution.

This script demonstrates how to use Daytona Cloud sandboxes
for isolated agent task execution.

Usage:
    # Config is loaded from .env.local and config/base.yaml
    uv run python examples/daytona_workspace_example.py

Config sources (in priority order):
    1. Environment variables: DAYTONA_API_KEY, DAYTONA_API_URL, etc.
    2. .env.local file
    3. config/base.yaml and config/<OMOIOS_ENV>.yaml

Get your API key from: https://app.daytona.io/dashboard/keys
"""

import os
import sys

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omoi_os.workspace import DaytonaWorkspace, DaytonaWorkspaceConfig


def main():
    # Load config from YAML/env (no manual API key needed)
    try:
        config = DaytonaWorkspaceConfig.from_settings(
            labels={"project": "omoios-test"},
        )
    except ValueError as e:
        print(f"Error: {e}")
        print("\nTo configure Daytona:")
        print("  1. Go to https://app.daytona.io/dashboard/keys")
        print("  2. Create a new key with Sandboxes permission")
        print("  3. Add to .env.local: DAYTONA_API_KEY=your-key")
        sys.exit(1)

    print("Creating Daytona sandbox...")
    print("-" * 50)

    # Use workspace with context manager (auto-cleanup)
    with DaytonaWorkspace(config) as workspace:
        print(f"✓ Sandbox created: {workspace.sandbox_id}")
        print()

        # Test 1: Execute basic command
        print("Test 1: Execute shell command")
        result = workspace.execute_command("echo 'Hello from Daytona!' && pwd")
        print(f"  stdout: {result.stdout.strip()}")
        print(f"  exit_code: {result.exit_code}")
        print()

        # Test 2: Check Python version
        print("Test 2: Check Python version")
        result = workspace.execute_command("python --version")
        print(f"  {result.stdout.strip()}")
        print()

        # Test 3: Write and read a file
        print("Test 3: File operations")
        workspace.write_file("/home/daytona/test.txt", "Hello, OmoiOS!")
        content = workspace.read_file("/home/daytona/test.txt")
        print(f"  Wrote and read: {content.decode()}")
        print()

        # Test 4: Create directory and list
        print("Test 4: Directory operations")
        workspace.create_folder("/home/daytona/myproject")
        result = workspace.execute_command("ls -la /home/daytona/")
        print(f"  Directory listing:\n{result.stdout}")

        # Test 5: Install a package and run code
        print("Test 5: Install package and run code")
        result = workspace.execute_command("pip install cowsay -q && python -c \"import cowsay; cowsay.cow('OmoiOS!')\"")
        print(f"{result.stdout}")

    print("-" * 50)
    print("✓ Sandbox automatically cleaned up")


async def async_example():
    """Async version of the example."""
    import asyncio

    try:
        config = DaytonaWorkspaceConfig.from_settings()
    except ValueError as e:
        print(f"Error: {e}")
        return

    print("Creating Daytona sandbox (async)...")

    async with DaytonaWorkspace(config) as workspace:
        print(f"✓ Sandbox: {workspace.sandbox_id}")

        # Execute commands asynchronously
        result = await workspace.execute_command_async("uname -a")
        print(f"System: {result.stdout.strip()}")

    print("✓ Sandbox cleaned up")


if __name__ == "__main__":
    # Run sync example
    main()

    # Uncomment to run async example:
    # import asyncio
    # asyncio.run(async_example())
