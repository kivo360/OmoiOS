#!/usr/bin/env python3
"""Query sandbox events from the database.

Usage:
    cd backend
    uv run python scripts/query_sandbox_events.py <sandbox_id>

Example:
    uv run python scripts/query_sandbox_events.py omoios-886da5fe-0a9fee
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

from omoi_os.services.database import DatabaseService
from omoi_os.config import get_app_settings


def query_events(sandbox_id: str, limit: int = 50):
    """Query events for a sandbox."""
    settings = get_app_settings()
    db = DatabaseService(connection_string=settings.database.url)

    from omoi_os.models.sandbox_event import SandboxEvent

    with db.get_session() as session:
        events = (
            session.query(SandboxEvent)
            .filter(SandboxEvent.sandbox_id == sandbox_id)
            .order_by(
                SandboxEvent.created_at.asc()
            )  # Oldest first for chronological view
            .limit(limit)
            .all()
        )

        if not events:
            print(f"No events found for sandbox: {sandbox_id}")
            return

        print(f"\n{'=' * 80}")
        print(f"Events for sandbox: {sandbox_id}")
        print(f"Total events: {len(events)}")
        print(f"{'=' * 80}\n")

        for i, event in enumerate(events, 1):
            print(f"[{i}] {event.event_type}")
            print(f"    Source: {event.source}")
            print(f"    Created: {event.created_at}")

            # Pretty print event_data
            if event.event_data:
                import json

                event_data_str = json.dumps(event.event_data, indent=2)
                # Truncate very long event data
                if len(event_data_str) > 500:
                    event_data_str = event_data_str[:500] + "... (truncated)"
                print("    Data:")
                for line in event_data_str.split("\n"):
                    print(f"      {line}")

            print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/query_sandbox_events.py <sandbox_id>")
        print("\nExample:")
        print("  python scripts/query_sandbox_events.py omoios-886da5fe-0a9fee")
        sys.exit(1)

    sandbox_id = sys.argv[1]
    query_events(sandbox_id)
