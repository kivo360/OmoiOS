#!/usr/bin/env python3
"""Cleanup/terminate Daytona sandboxes and clear database references.

Usage:
    python scripts/cleanup_sandboxes.py                    # List all sandboxes
    python scripts/cleanup_sandboxes.py --terminate-all     # Terminate all STARTED sandboxes
    python scripts/cleanup_sandboxes.py --terminate <id>    # Terminate specific sandbox
    python scripts/cleanup_sandboxes.py --cleanup-db        # Clear sandbox_id from tasks in DB
"""

import sys
import os

# Add parent directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService


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


def cleanup_database_sandboxes():
    """Clear sandbox_id from tasks in database and reset task statuses."""
    try:
        from omoi_os.config import get_app_settings

        settings = get_app_settings()
        db = DatabaseService(connection_string=settings.database.url)

        with db.get_session() as session:
            from omoi_os.models.task import Task

            # Find all tasks with sandbox_id
            tasks_with_sandbox = (
                session.query(Task).filter(Task.sandbox_id.isnot(None)).all()
            )

            if not tasks_with_sandbox:
                print("No tasks with sandbox_id found in database")
                return

            print(f"\nFound {len(tasks_with_sandbox)} task(s) with sandbox_id:")

            updated = 0
            for task in tasks_with_sandbox:
                print(
                    f"  - Task {task.id[:8]}... (sandbox_id: {task.sandbox_id}, status: {task.status})"
                )

                # Clear sandbox_id
                task.sandbox_id = None

                # Reset status if it's still assigned/running (likely stale)
                if task.status in ["assigned", "running"]:
                    task.status = "pending"
                    print(f"    → Reset status from {task.status} to pending")

                updated += 1

            session.commit()
            print(f"\n✅ Updated {updated} task(s) in database")
            print("   - Cleared sandbox_id references")
            print("   - Reset stale assigned/running tasks to pending")

    except Exception as e:
        print(f"❌ Error cleaning up database: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--terminate-all":
            terminate_all_started()
        elif sys.argv[1] == "--terminate" and len(sys.argv) > 2:
            terminate_sandbox(sys.argv[2])
        elif sys.argv[1] == "--cleanup-db":
            cleanup_database_sandboxes()
        elif sys.argv[1] == "--full-cleanup":
            # Full cleanup: terminate sandboxes AND clean database
            print("=" * 70)
            print("🧹 FULL CLEANUP: Terminating sandboxes and cleaning database")
            print("=" * 70)
            terminate_all_started()
            print()
            cleanup_database_sandboxes()
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
            print(
                "  python scripts/cleanup_sandboxes.py --cleanup-db        # Clear sandbox_id from tasks in DB"
            )
            print(
                "  python scripts/cleanup_sandboxes.py --full-cleanup       # Terminate sandboxes AND clean DB"
            )
    else:
        list_sandboxes()
