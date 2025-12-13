#!/usr/bin/env python3
"""Fetch logs from a Daytona sandbox.

Usage:
    python scripts/get_sandbox_logs.py <sandbox_id>

Example:
    python scripts/get_sandbox_logs.py omoios-c32baf9f-f642a2
"""

import sys
import os

# Add parent directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from omoi_os.config import get_app_settings


def get_sandbox_logs(sandbox_id: str):
    """Connect to a Daytona sandbox and fetch worker logs."""
    try:
        from daytona import Daytona, DaytonaConfig

        settings = get_app_settings()

        config = DaytonaConfig(
            api_key=settings.daytona.api_key,
            api_url=settings.daytona.api_url,
            target="us",
        )

        daytona = Daytona(config)

        print(f"Connecting to sandbox: {sandbox_id}")

        # Get sandbox directly by ID
        try:
            target_sandbox = daytona.get(sandbox_id)
        except Exception as e:
            print(f"Could not get sandbox directly: {e}")
            print("Trying to find by task_id label...")

            # Try to find by label
            result = daytona.list()
            sandboxes = getattr(result, "sandboxes", result)

            target_sandbox = None
            for sb in sandboxes:
                labels = getattr(sb, "labels", {}) or {}
                task_id = labels.get("task_id", "")
                # Match either full ID or task_id label
                if (
                    sb.id == sandbox_id
                    or task_id == sandbox_id
                    or sandbox_id in str(sb.id)
                ):
                    target_sandbox = sb
                    break

            if not target_sandbox:
                print("Sandbox not found.")
                return

        print(
            f"Found sandbox: {target_sandbox.id} (state: {getattr(target_sandbox, 'state', 'unknown')})"
        )

        # Get the worker log
        print("\n=== Worker Log (/tmp/worker.log) ===")
        try:
            result = target_sandbox.process.exec(
                "cat /tmp/worker.log 2>/dev/null || echo '[No log file yet]'"
            )
            print(result.result if hasattr(result, "result") else result)
        except Exception as e:
            print(f"Error reading log: {e}")

        # Check if worker process is running
        print("\n=== Worker Process Status ===")
        try:
            result = target_sandbox.process.exec(
                "ps aux | grep -E 'sandbox_worker|python' | grep -v grep || echo '[No python process]'"
            )
            print(result.result if hasattr(result, "result") else result)
        except Exception as e:
            print(f"Error checking process: {e}")

        # Check environment
        print("\n=== Environment (/tmp/.sandbox_env) ===")
        try:
            result = target_sandbox.process.exec(
                "cat /tmp/.sandbox_env 2>/dev/null | head -20 || echo '[No env file]'"
            )
            output = result.result if hasattr(result, "result") else str(result)
            # Mask sensitive values
            for line in output.split("\n"):
                if "API_KEY" in line or "TOKEN" in line or "SECRET" in line:
                    key = line.split("=")[0] if "=" in line else line
                    print(f"{key}=[MASKED]")
                else:
                    print(line)
        except Exception as e:
            print(f"Error reading env: {e}")

    except ImportError as e:
        print(f"Daytona SDK not installed: {e}")
        print("Run: pip install daytona-sdk")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


def list_sandboxes():
    """List all available sandboxes."""
    try:
        from daytona import Daytona, DaytonaConfig

        settings = get_app_settings()

        config = DaytonaConfig(
            api_key=settings.daytona.api_key,
            api_url=settings.daytona.api_url,
            target="us",
        )

        daytona = Daytona(config)
        result = daytona.list()

        # Handle paginated response
        sandboxes = (
            getattr(result, "items", result)
            if hasattr(result, "items")
            else list(result)
        )
        if hasattr(result, "sandboxes"):
            sandboxes = result.sandboxes

        print(f"Found {len(sandboxes)} sandboxes:\n")
        for sb in sandboxes[:20]:  # Limit to first 20
            labels = getattr(sb, "labels", {}) or {}
            state = getattr(sb, "state", "unknown")
            created = getattr(sb, "created_at", "")
            print(f"  ID: {sb.id}")
            print(f"  State: {state}")
            print(f"  Labels: {labels}")
            print(f"  Created: {created}")
            print()

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/get_sandbox_logs.py <sandbox_id>")
        print("       python scripts/get_sandbox_logs.py --list")
        print("\nListing available sandboxes...")
        list_sandboxes()
    elif sys.argv[1] == "--list":
        list_sandboxes()
    else:
        get_sandbox_logs(sys.argv[1])
