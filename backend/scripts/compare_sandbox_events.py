#!/usr/bin/env python3
"""Compare event types across multiple sandboxes.

Usage:
    cd backend
    uv run python scripts/compare_sandbox_events.py [sandbox_id1] [sandbox_id2] ...

If no sandbox IDs provided, shows summary of all recent sandboxes.
"""

import sys
from pathlib import Path
from collections import Counter

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

from omoi_os.services.database import DatabaseService
from omoi_os.config import get_app_settings


def get_event_summary(sandbox_id: str):
    """Get event type summary for a sandbox."""
    settings = get_app_settings()
    db = DatabaseService(connection_string=settings.database.url)

    from omoi_os.models.sandbox_event import SandboxEvent

    with db.get_session() as session:
        events = (
            session.query(SandboxEvent)
            .filter(SandboxEvent.sandbox_id == sandbox_id)
            .order_by(SandboxEvent.created_at.asc())
            .all()
        )

        if not events:
            return None

        event_types = [e.event_type for e in events]
        event_counter = Counter(event_types)

        # Get first and last event times
        first_event = events[0].created_at
        last_event = events[-1].created_at
        duration = (last_event - first_event).total_seconds()

        # Check for completion
        has_completed = any(e.event_type == "agent.completed" for e in events)
        has_error = any(
            e.event_type in ["agent.stream_error", "agent.error"] for e in events
        )

        return {
            "sandbox_id": sandbox_id,
            "total_events": len(events),
            "event_types": dict(event_counter),
            "first_event": first_event,
            "last_event": last_event,
            "duration_seconds": duration,
            "completed": has_completed,
            "has_error": has_error,
            "events": events,
        }


def list_recent_sandbox_ids(limit: int = 10):
    """Get list of recent sandbox IDs."""
    settings = get_app_settings()
    db = DatabaseService(connection_string=settings.database.url)

    from omoi_os.models.sandbox_event import SandboxEvent
    from sqlalchemy import func

    with db.get_session() as session:
        results = (
            session.query(SandboxEvent.sandbox_id)
            .group_by(SandboxEvent.sandbox_id)
            .order_by(func.max(SandboxEvent.created_at).desc())
            .limit(limit)
            .all()
        )
        return [r[0] for r in results]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        sandbox_ids = sys.argv[1:]
    else:
        print("No sandbox IDs provided. Fetching recent sandboxes...")
        sandbox_ids = list_recent_sandbox_ids(limit=5)
        print(f"Found {len(sandbox_ids)} recent sandboxes\n")

    summaries = []
    for sandbox_id in sandbox_ids:
        summary = get_event_summary(sandbox_id)
        if summary:
            summaries.append(summary)
        else:
            print(f"⚠️  No events found for sandbox: {sandbox_id}")

    if not summaries:
        print("No sandbox events found.")
        sys.exit(1)

    print(f"\n{'=' * 120}")
    print("Event Summary Comparison")
    print(f"{'=' * 120}\n")

    # Print summary table
    print(
        f"{'Sandbox ID':<40} {'Total':<8} {'Duration':<12} {'Status':<12} {'Key Events'}"
    )
    print("-" * 120)

    for summary in summaries:
        status = "✅ Completed" if summary["completed"] else "❌ Incomplete"
        if summary["has_error"]:
            status = "⚠️  Error"

        # Get key event counts
        key_events = []
        for event_type in [
            "agent.started",
            "agent.tool_use",
            "agent.file_edited",
            "agent.completed",
        ]:
            count = summary["event_types"].get(event_type, 0)
            if count > 0:
                key_events.append(f"{event_type.split('.')[-1]}:{count}")

        duration_str = f"{summary['duration_seconds']:.1f}s"
        print(
            f"{summary['sandbox_id']:<40} {summary['total_events']:<8} {duration_str:<12} {status:<12} {', '.join(key_events)}"
        )

    print(f"\n{'=' * 120}")
    print("Detailed Event Type Breakdown")
    print(f"{'=' * 120}\n")

    for summary in summaries:
        print(f"\n📦 {summary['sandbox_id']}")
        print(f"   Total: {summary['total_events']} events")
        print(f"   Duration: {summary['duration_seconds']:.1f} seconds")
        print(
            f"   Status: {'✅ Completed' if summary['completed'] else '❌ Incomplete'}"
        )
        if summary["has_error"]:
            print("   ⚠️  Contains errors")

        print("   Event Types:")
        for event_type, count in sorted(summary["event_types"].items()):
            print(f"      - {event_type}: {count}")
