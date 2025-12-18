#!/usr/bin/env python3
"""List recent sandboxes and their event counts.

Usage:
    cd backend
    uv run python scripts/list_recent_sandboxes.py [--limit N]
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

from omoi_os.services.database import DatabaseService
from omoi_os.config import get_app_settings


def list_recent_sandboxes(limit: int = 20):
    """List recent sandboxes with event counts."""
    settings = get_app_settings()
    db = DatabaseService(connection_string=settings.database.url)

    from omoi_os.models.sandbox_event import SandboxEvent
    from sqlalchemy import func

    with db.get_session() as session:
        # Get sandboxes grouped by sandbox_id with event counts and latest event time
        results = (
            session.query(
                SandboxEvent.sandbox_id,
                func.count(SandboxEvent.id).label("event_count"),
                func.max(SandboxEvent.created_at).label("latest_event"),
                func.min(SandboxEvent.created_at).label("first_event"),
            )
            .group_by(SandboxEvent.sandbox_id)
            .order_by(func.max(SandboxEvent.created_at).desc())
            .limit(limit)
            .all()
        )

        if not results:
            print("No sandboxes found in database.")
            return

        print(f"\n{'=' * 100}")
        print(f"Recent Sandboxes (last {limit})")
        print(f"{'=' * 100}\n")
        print(
            f"{'Sandbox ID':<40} {'Events':<10} {'First Event':<25} {'Latest Event':<25}"
        )
        print("-" * 100)

        for sandbox_id, event_count, latest_event, first_event in results:
            print(
                f"{sandbox_id:<40} {event_count:<10} {first_event.strftime('%Y-%m-%d %H:%M:%S') if first_event else 'N/A':<25} {latest_event.strftime('%Y-%m-%d %H:%M:%S') if latest_event else 'N/A':<25}"
            )

        print()

        # Also check for tasks to see which sandboxes are associated with tasks
        from omoi_os.models.task import Task

        print(f"\n{'=' * 100}")
        print("Sandboxes with Task Associations")
        print(f"{'=' * 100}\n")
        print(f"{'Sandbox ID':<40} {'Task ID':<40} {'Status':<15} {'Created':<25}")
        print("-" * 100)

        tasks = (
            session.query(Task)
            .filter(Task.sandbox_id.isnot(None))
            .order_by(Task.created_at.desc())
            .limit(limit)
            .all()
        )

        for task in tasks:
            print(
                f"{task.sandbox_id:<40} {str(task.id):<40} {task.status:<15} {task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else 'N/A':<25}"
            )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="List recent sandboxes")
    parser.add_argument(
        "--limit", type=int, default=20, help="Maximum number of sandboxes to show"
    )
    args = parser.parse_args()

    list_recent_sandboxes(limit=args.limit)
