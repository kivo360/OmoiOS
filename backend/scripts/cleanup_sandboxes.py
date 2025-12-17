#!/usr/bin/env python3
"""Cleanup/terminate Daytona sandboxes.

Usage:
    python scripts/cleanup_sandboxes.py                    # List all sandboxes
    python scripts/cleanup_sandboxes.py --terminate-all     # Terminate all STARTED sandboxes
    python scripts/cleanup_sandboxes.py --terminate <id>    # Terminate specific sandbox
"""

import sys
import os

# Add parent directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from omoi_os.config import get_app_settings


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
        for sb in sandboxes:
            labels = getattr(sb, "labels", {}) or {}
            state = getattr(sb, "state", "unknown")
            created = getattr(sb, "created_at", "")
            print(f"  ID: {sb.id}")
            print(f"  State: {state}")
            print(f"  Labels: {labels}")
            print(f"  Created: {created}")
            print()

        return sandboxes

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return []


def terminate_sandbox(sandbox_id: str) -> bool:
    """Terminate a specific sandbox."""
    try:
        from daytona import Daytona, DaytonaConfig

        settings = get_app_settings()

        config = DaytonaConfig(
            api_key=settings.daytona.api_key,
            api_url=settings.daytona.api_url,
            target="us",
        )

        daytona = Daytona(config)

        # Get sandbox
        try:
            sandbox = daytona.get(sandbox_id)
        except Exception as e:
            print(f"Could not get sandbox {sandbox_id}: {e}")
            # Try to find by label
            result = daytona.list()
            sandboxes = (
                getattr(result, "items", result)
                if hasattr(result, "items")
                else list(result)
            )
            if hasattr(result, "sandboxes"):
                sandboxes = result.sandboxes

            sandbox = None
            for sb in sandboxes:
                if sb.id == sandbox_id or sandbox_id in str(sb.id):
                    sandbox = sb
                    break

            if not sandbox:
                print(f"Sandbox {sandbox_id} not found")
                return False

        # Delete/terminate sandbox
        print(f"Terminating sandbox: {sandbox.id}...")
        sandbox.delete()
        print(f"✅ Sandbox {sandbox.id} terminated")
        return True

    except Exception as e:
        print(f"❌ Error terminating sandbox {sandbox_id}: {e}")
        import traceback

        traceback.print_exc()
        return False


def terminate_all_started():
    """Terminate all STARTED sandboxes."""
    sandboxes = list_sandboxes()

    if not sandboxes:
        print("No sandboxes found")
        return

    started_sandboxes = [
        sb
        for sb in sandboxes
        if getattr(sb, "state", "").__str__() == "SandboxState.STARTED"
    ]

    if not started_sandboxes:
        print("No STARTED sandboxes to terminate")
        return

    print(f"\nTerminating {len(started_sandboxes)} STARTED sandbox(es)...\n")

    terminated = 0
    for sb in started_sandboxes:
        if terminate_sandbox(sb.id):
            terminated += 1

    print(f"\n✅ Terminated {terminated}/{len(started_sandboxes)} sandbox(es)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--terminate-all":
            terminate_all_started()
        elif sys.argv[1] == "--terminate" and len(sys.argv) > 2:
            terminate_sandbox(sys.argv[2])
        else:
            print("Usage:")
            print(
                "  python scripts/cleanup_sandboxes.py                    # List all sandboxes"
            )
            print(
                "  python scripts/cleanup_sandboxes.py --terminate-all     # Terminate all STARTED sandboxes"
            )
            print(
                "  python scripts/cleanup_sandboxes.py --terminate <id>    # Terminate specific sandbox"
            )
    else:
        list_sandboxes()
