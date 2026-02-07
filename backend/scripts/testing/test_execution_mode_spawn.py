#!/usr/bin/env python3
"""Test spawning sandboxes with different execution modes.

This script allows you to spawn a sandbox for an existing ticket/task
with a specific execution mode to verify the correct skills and prompts
are loaded.

Usage:
    cd backend

    # List available tickets
    uv run python scripts/testing/test_execution_mode_spawn.py --list-tickets

    # List tasks for a ticket
    uv run python scripts/testing/test_execution_mode_spawn.py --list-tasks <ticket_id>

    # Spawn with auto-detected mode (based on task_type)
    uv run python scripts/testing/test_execution_mode_spawn.py --task <task_id>

    # Spawn with explicit mode override
    uv run python scripts/testing/test_execution_mode_spawn.py --task <task_id> --mode exploration
    uv run python scripts/testing/test_execution_mode_spawn.py --task <task_id> --mode implementation
    uv run python scripts/testing/test_execution_mode_spawn.py --task <task_id> --mode validation

    # Dry run (show what would happen without spawning)
    uv run python scripts/testing/test_execution_mode_spawn.py --task <task_id> --dry-run
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env.local")

from omoi_os.config import get_app_settings


def get_db():
    """Get database service with proper connection string."""
    from omoi_os.services.database import DatabaseService

    app_settings = get_app_settings()
    return DatabaseService(connection_string=app_settings.database.url)


def list_tickets(limit: int = 20):
    """List recent tickets."""
    from omoi_os.models.ticket import Ticket

    db = get_db()
    with db.get_session() as session:
        tickets = (
            session.query(Ticket).order_by(Ticket.created_at.desc()).limit(limit).all()
        )

        if not tickets:
            print("No tickets found.")
            return

        print(f"\n{'ID':<40} {'Status':<15} {'Title':<50}")
        print("-" * 105)
        for t in tickets:
            title = (
                (t.title or "Untitled")[:47] + "..."
                if len(t.title or "") > 50
                else (t.title or "Untitled")
            )
            print(f"{t.id:<40} {t.status:<15} {title:<50}")


def list_tasks(ticket_id: str):
    """List tasks for a ticket."""
    from omoi_os.models.task import Task

    db = get_db()
    with db.get_session() as session:
        tasks = (
            session.query(Task)
            .filter(Task.ticket_id == ticket_id)
            .order_by(Task.created_at.desc())
            .all()
        )

        if not tasks:
            print(f"No tasks found for ticket {ticket_id}")
            return

        print(f"\nTasks for ticket: {ticket_id}")
        print(f"\n{'ID':<40} {'Type':<25} {'Status':<15} {'Phase':<20}")
        print("-" * 100)
        for t in tasks:
            print(f"{t.id:<40} {t.task_type:<25} {t.status:<15} {t.phase_id:<20}")


def get_task_details(task_id: str):
    """Get full task details including ticket info."""
    from sqlalchemy.orm import joinedload
    from omoi_os.models.task import Task
    from omoi_os.models.ticket import Ticket

    db = get_db()
    with db.get_session() as session:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            print(f"Task {task_id} not found")
            return None, None, None

        # Eagerly load ticket with project relationship
        ticket = (
            session.query(Ticket)
            .options(joinedload(Ticket.project))
            .filter(Ticket.id == task.ticket_id)
            .first()
        )

        # Extract project info before detaching
        project_info = None
        if ticket and ticket.project:
            project_info = {
                "name": getattr(ticket.project, "name", None),
                "github_owner": getattr(ticket.project, "github_owner", None),
                "github_repo": getattr(ticket.project, "github_repo", None),
            }

        # Detach from session for return
        session.expunge(task)
        if ticket:
            session.expunge(ticket)

        return task, ticket, project_info


async def spawn_sandbox(
    task_id: str,
    mode_override: str = None,
    dry_run: bool = False,
):
    """Spawn a sandbox for a task with specified execution mode."""
    from omoi_os.workers.orchestrator_worker import get_execution_mode
    from omoi_os.sandbox_skills import get_skills_for_upload
    from omoi_os.config import load_daytona_settings

    # Get task details
    task, ticket, project_info = get_task_details(task_id)
    if not task:
        return

    # Determine execution mode
    auto_mode = get_execution_mode(task.task_type)
    execution_mode = mode_override or auto_mode

    print("\n" + "=" * 60)
    print("🧪 EXECUTION MODE SPAWN TEST")
    print("=" * 60)

    print("\n📋 Task Details:")
    print(f"   Task ID: {task.id}")
    print(f"   Task Type: {task.task_type}")
    print(f"   Status: {task.status}")
    print(f"   Phase: {task.phase_id}")
    if task.description:
        desc = (
            task.description[:100] + "..."
            if len(task.description) > 100
            else task.description
        )
        print(f"   Description: {desc}")

    if ticket:
        print("\n📝 Ticket Details:")
        print(f"   Ticket ID: {ticket.id}")
        print(f"   Title: {ticket.title}")
        if project_info:
            print(f"   Project: {project_info.get('name', 'Unknown')}")

    print("\n🎯 Execution Mode:")
    print(f"   Auto-detected: {auto_mode}")
    if mode_override:
        print(f"   Override: {mode_override}")
    print(f"   Using: {execution_mode}")

    # Get skills for this mode
    skills = get_skills_for_upload(mode=execution_mode)
    skill_names = set()
    for path in skills.keys():
        parts = path.split("/")
        if "skills" in parts:
            idx = parts.index("skills")
            if idx + 1 < len(parts):
                skill_names.add(parts[idx + 1])

    print("\n📦 Skills to Load:")
    for skill in sorted(skill_names):
        marker = "📝" if skill == "spec-driven-dev" else "🔧"
        print(f"   {marker} {skill}")

    has_spec_skill = "spec-driven-dev" in skill_names
    print(f"\n   spec-driven-dev included: {'✅ Yes' if has_spec_skill else '❌ No'}")

    if dry_run:
        print("\n🔍 DRY RUN - Not spawning actual sandbox")
        print("   Would spawn sandbox with:")
        print(f"   - execution_mode={execution_mode}")
        print("   - runtime=claude")
        print(f"   - skills={sorted(skill_names)}")
        return

    # Check Daytona settings
    daytona_settings = load_daytona_settings()
    if not daytona_settings.api_key:
        print("\n❌ DAYTONA_API_KEY not set - cannot spawn sandbox")
        return

    print(f"\n✅ Daytona API Key: {daytona_settings.api_key[:12]}...")

    # Import and create spawner
    from omoi_os.services.daytona_spawner import DaytonaSpawnerService

    db = get_db()
    spawner = DaytonaSpawnerService(
        db=db,
        event_bus=None,
        mcp_server_url="http://localhost:18000/mcp/",
    )

    # Build extra_env similar to orchestrator
    extra_env = {
        "TICKET_ID": str(ticket.id) if ticket else "",
        "TICKET_TITLE": ticket.title if ticket else "",
    }

    # Add project info if available
    if project_info:
        github_owner = project_info.get("github_owner")
        github_repo = project_info.get("github_repo")
        if github_owner and github_repo:
            extra_env["GITHUB_REPO"] = f"{github_owner}/{github_repo}"
            extra_env["GITHUB_REPO_OWNER"] = github_owner
            extra_env["GITHUB_REPO_NAME"] = github_repo

    agent_id = f"test-agent-{uuid4().hex[:8]}"

    print("\n🚀 Spawning sandbox...")
    print(f"   Agent ID: {agent_id}")
    print(f"   Execution Mode: {execution_mode}")

    try:
        start_time = time.time()
        sandbox_id = await spawner.spawn_for_task(
            task_id=task_id,
            agent_id=agent_id,
            phase_id=task.phase_id,
            agent_type="worker",
            extra_env=extra_env,
            runtime="claude",
            execution_mode=execution_mode,
        )
        spawn_time = time.time() - start_time

        print(f"\n✅ Sandbox spawned in {spawn_time:.1f}s")
        print(f"   Sandbox ID: {sandbox_id}")

        # Get sandbox info
        info = spawner.get_sandbox_info(sandbox_id)
        if info:
            print(f"   Status: {info.status}")

        # Verify skills were uploaded
        sandbox = info.extra_data.get("daytona_sandbox") if info else None
        if sandbox:
            print("\n🔍 Verifying skills in sandbox...")
            result = sandbox.process.exec(
                "ls -la /root/.claude/skills/ 2>/dev/null || echo 'Skills dir not found'"
            )
            print("   Skills directory:")
            for line in result.result.strip().split("\n"):
                print(f"      {line}")

            # Check environment variables (use . instead of source for sh compatibility)
            result = sandbox.process.exec(". /root/.bashrc && echo $EXECUTION_MODE")
            print(f"\n   EXECUTION_MODE env var: {result.result.strip()}")

            # Also check /tmp/.sandbox_env file for persistent env vars
            result = sandbox.process.exec(
                "cat /tmp/.sandbox_env | grep EXECUTION_MODE || echo 'Not in file'"
            )
            print(f"   EXECUTION_MODE in env file: {result.result.strip()}")

        print("\n🎉 Sandbox ready for testing!")
        print(f"   You can connect to: {sandbox_id}")

        # Ask if user wants to terminate
        print("\n⚠️  Remember to terminate the sandbox when done:")
        print(f"   await spawner.terminate_sandbox('{sandbox_id}')")

    except Exception as e:
        print(f"\n❌ Failed to spawn sandbox: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(
        description="Test spawning sandboxes with different execution modes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--list-tickets", action="store_true", help="List recent tickets"
    )
    parser.add_argument(
        "--list-tasks", metavar="TICKET_ID", help="List tasks for a ticket"
    )
    parser.add_argument(
        "--task", metavar="TASK_ID", help="Task ID to spawn sandbox for"
    )
    parser.add_argument(
        "--mode",
        choices=["exploration", "implementation", "validation"],
        help="Override execution mode (default: auto-detect from task_type)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would happen without spawning"
    )

    args = parser.parse_args()

    if args.list_tickets:
        list_tickets()
    elif args.list_tasks:
        list_tasks(args.list_tasks)
    elif args.task:
        asyncio.run(
            spawn_sandbox(
                task_id=args.task,
                mode_override=args.mode,
                dry_run=args.dry_run,
            )
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
