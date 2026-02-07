#!/usr/bin/env python3
"""
Fix ticket phase_id values for board display.

This script updates tickets with incorrect phase_id values (like 'backlog')
to the correct format ('PHASE_BACKLOG') so they appear on the kanban board.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update, func
from omoi_os.config import get_app_settings
from omoi_os.services.database import DatabaseService
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task

# Mapping of incorrect -> correct phase_id values
PHASE_ID_FIXES = {
    "backlog": "PHASE_BACKLOG",
    "requirements": "PHASE_REQUIREMENTS",
    "design": "PHASE_DESIGN",
    "implementation": "PHASE_IMPLEMENTATION",
    "testing": "PHASE_TESTING",
    "deployment": "PHASE_DEPLOYMENT",
    "done": "PHASE_DONE",
    "blocked": "PHASE_BLOCKED",
}


async def fix_ticket_phase_ids(dry_run: bool = True) -> dict:
    """Fix ticket phase_id values."""
    settings = get_app_settings()
    db = DatabaseService(connection_string=settings.database.url)

    results = {
        "tickets_checked": 0,
        "tickets_fixed": 0,
        "tasks_checked": 0,
        "tasks_fixed": 0,
        "fixes_by_phase": {},
    }

    async with db.get_async_session() as session:
        # Check for tickets with incorrect phase_id
        for old_phase, new_phase in PHASE_ID_FIXES.items():
            # Count tickets with this incorrect phase_id
            count_result = await session.execute(
                select(func.count(Ticket.id)).where(Ticket.phase_id == old_phase)
            )
            ticket_count = count_result.scalar() or 0

            # Count tasks with this incorrect phase_id
            task_count_result = await session.execute(
                select(func.count(Task.id)).where(Task.phase_id == old_phase)
            )
            task_count = task_count_result.scalar() or 0

            if ticket_count > 0 or task_count > 0:
                results["fixes_by_phase"][old_phase] = {
                    "tickets": ticket_count,
                    "tasks": task_count,
                    "new_value": new_phase,
                }

                if not dry_run:
                    # Update tickets
                    if ticket_count > 0:
                        await session.execute(
                            update(Ticket)
                            .where(Ticket.phase_id == old_phase)
                            .values(phase_id=new_phase)
                        )
                        results["tickets_fixed"] += ticket_count

                    # Update tasks
                    if task_count > 0:
                        await session.execute(
                            update(Task)
                            .where(Task.phase_id == old_phase)
                            .values(phase_id=new_phase)
                        )
                        results["tasks_fixed"] += task_count

        # Also check for NULL phase_id on tickets
        null_count_result = await session.execute(
            select(func.count(Ticket.id)).where(Ticket.phase_id.is_(None))
        )
        null_ticket_count = null_count_result.scalar() or 0

        if null_ticket_count > 0:
            results["fixes_by_phase"]["NULL"] = {
                "tickets": null_ticket_count,
                "tasks": 0,
                "new_value": "PHASE_BACKLOG",
            }

            if not dry_run:
                await session.execute(
                    update(Ticket)
                    .where(Ticket.phase_id.is_(None))
                    .values(phase_id="PHASE_BACKLOG")
                )
                results["tickets_fixed"] += null_ticket_count

        if not dry_run:
            await session.commit()

        # Get total counts
        total_tickets = await session.execute(select(func.count(Ticket.id)))
        total_tasks = await session.execute(select(func.count(Task.id)))
        results["tickets_checked"] = total_tickets.scalar() or 0
        results["tasks_checked"] = total_tasks.scalar() or 0

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fix ticket phase_id values for board display"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the fixes (default is dry-run)",
    )
    args = parser.parse_args()

    dry_run = not args.apply

    print("=" * 60)
    print("Ticket Phase ID Fixer")
    print("=" * 60)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'APPLYING CHANGES'}")
    print()

    results = asyncio.run(fix_ticket_phase_ids(dry_run=dry_run))

    print(f"Tickets checked: {results['tickets_checked']}")
    print(f"Tasks checked: {results['tasks_checked']}")
    print()

    if results["fixes_by_phase"]:
        print("Fixes needed:")
        for old_phase, info in results["fixes_by_phase"].items():
            print(f"  '{old_phase}' -> '{info['new_value']}':")
            print(f"    Tickets: {info['tickets']}")
            print(f"    Tasks: {info['tasks']}")
        print()

        if dry_run:
            total_tickets = sum(
                v["tickets"] for v in results["fixes_by_phase"].values()
            )
            total_tasks = sum(v["tasks"] for v in results["fixes_by_phase"].values())
            print(f"Total to fix: {total_tickets} tickets, {total_tasks} tasks")
            print()
            print("Run with --apply to fix these issues")
        else:
            print(
                f"Fixed: {results['tickets_fixed']} tickets, {results['tasks_fixed']} tasks"
            )
    else:
        print("No fixes needed - all phase_id values are correct!")

    print("=" * 60)


if __name__ == "__main__":
    main()
