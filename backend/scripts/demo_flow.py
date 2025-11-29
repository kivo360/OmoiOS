#!/usr/bin/env python3
"""
Demo: Full OmoiOS Flow - From Prompt to Execution

This demonstrates the Claude Code / Cursor Agents-like workflow:
1. User submits a prompt (creates a ticket)
2. Ticket gets approved (auto or manual)
3. Task is created and assigned
4. Agent executes with OpenHands
5. Agent reports back via MCP tools

Usage:
    uv run python scripts/demo_flow.py "Build a hello world script"
    uv run python scripts/demo_flow.py "Create a fibonacci function" --auto-execute
"""

import argparse
import tempfile
from uuid import uuid4

from omoi_os.config import get_app_settings
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.agent_executor import AgentExecutor
from omoi_os.utils.datetime import utc_now


def print_step(step: int, message: str):
    """Print a step with formatting."""
    print(f"\n{'=' * 60}")
    print(f"  Step {step}: {message}")
    print(f"{'=' * 60}")


def print_info(label: str, value: str):
    """Print info with formatting."""
    print(f"  {label}: {value}")


def create_ticket(db: DatabaseService, prompt: str, project_id: str = None) -> dict:
    """Create a ticket from the user's prompt."""
    from sqlalchemy import text

    ticket_id = str(uuid4())

    with db.get_session() as session:
        # Use raw SQL to insert with all fields including ticketing module fields
        session.execute(
            text("""
            INSERT INTO tickets (
                id, title, description, phase_id, status, priority,
                approval_status, project_id, workflow_id, created_by_agent_id,
                ticket_type, created_at, updated_at, is_blocked
            ) VALUES (
                :id, :title, :description, :phase_id, :status, :priority,
                :approval_status, :project_id, :workflow_id, :created_by_agent_id,
                :ticket_type, NOW(), NOW(), FALSE
            )
        """),
            {
                "id": ticket_id,
                "title": prompt[:100],
                "description": prompt,
                "phase_id": "PHASE_IMPLEMENTATION",
                "status": "backlog",
                "priority": "MEDIUM",
                "approval_status": "pending",
                "project_id": project_id,
                "workflow_id": "demo",
                "created_by_agent_id": "user",
                "ticket_type": "task",
            },
        )
        session.commit()

    return {"id": ticket_id, "title": prompt[:100], "status": "backlog"}


def approve_ticket(
    db: DatabaseService, queue: TaskQueueService, ticket_id: str
) -> Task:
    """Approve a ticket and create the first task."""
    with db.get_session() as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Approve the ticket
        ticket.approval_status = "approved"
        ticket.status = "analyzing"

        # Create the first task
        task = queue.enqueue_task(
            ticket_id=ticket_id,
            phase_id=ticket.phase_id,
            task_type="implementation",
            description=f"Implement: {ticket.description}",
            priority=ticket.priority,
            session=session,
        )

        session.commit()

        return {
            "id": str(task.id),
            "description": task.description[:60],
            "status": task.status,
        }


def execute_task(
    db: DatabaseService, queue: TaskQueueService, task_id: str, workspace_dir: str
) -> dict:
    """Execute a task using the AgentExecutor."""
    # Get task details
    with db.get_session() as session:
        task = session.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        ticket = session.get(Ticket, task.ticket_id)
        task_description = task.description
        ticket_id = task.ticket_id
        ticket_title = ticket.title if ticket else "Unknown"
        phase_id = task.phase_id

        # Mark task as running
        task.status = "running"
        task.started_at = utc_now()
        session.commit()

    # Create executor
    executor = AgentExecutor(
        phase_id=phase_id,
        workspace_dir=workspace_dir,
        db=db,
        planning_mode=False,
    )

    # Build the task prompt with MCP tool instructions
    full_prompt = f"""You are working on ticket {ticket_id}: "{ticket_title}"

TASK: {task_description}

WORKFLOW:
1. Implement the requested functionality
2. Test that it works
3. Add a comment using mcp__call_tool:
   Action: CallMCPToolAction
   Arguments:
     tool_name: "add_ticket_comment"
     arguments: {{"ticket_id": "{ticket_id}", "agent_id": "demo-agent", "comment_text": "Implementation complete with testing", "comment_type": "update"}}

4. Mark ticket complete using mcp__call_tool:
   Action: CallMCPToolAction
   Arguments:
     tool_name: "resolve_ticket"
     arguments: {{"ticket_id": "{ticket_id}", "agent_id": "demo-agent", "resolution_comment": "Task completed successfully"}}

IMPORTANT: When using mcp__call_tool, the tool_name should be the MCP server tool name (like "resolve_ticket"), NOT with _mcp suffix.

Start implementing now.
"""

    # Execute
    result = executor.execute_task(
        task_description=full_prompt,
        task_id=task_id,
    )

    # Update task status based on result
    status = (
        "completed"
        if result.get("status") and "FINISHED" in str(result.get("status"))
        else "failed"
    )

    with db.get_session() as session:
        task = session.get(Task, task_id)
        if task:
            task.status = status
            task.completed_at = utc_now()
            task.result = {"agent_result": str(result.get("status"))}
            session.commit()

    return {
        "status": status,
        "conversation_id": result.get("conversation_id"),
        "workspace": workspace_dir,
    }


def check_ticket_status(db: DatabaseService, ticket_id: str) -> dict:
    """Check the final status of a ticket."""
    from sqlalchemy import text

    with db.get_session() as session:
        result = session.execute(
            text("""
            SELECT id, title, status, is_resolved, resolved_at 
            FROM tickets WHERE id = :ticket_id
        """),
            {"ticket_id": ticket_id},
        )
        row = result.fetchone()

        if not row:
            return {"error": "Ticket not found"}

        return {
            "id": row[0],
            "title": row[1],
            "status": row[2],
            "is_resolved": row[3],
            "resolved_at": str(row[4]) if row[4] else None,
        }


def list_tickets(db: DatabaseService, limit: int = 10) -> list:
    """List recent tickets."""
    from sqlalchemy import text

    with db.get_session() as session:
        result = session.execute(
            text("""
            SELECT id, title, status, approval_status, is_resolved, created_at
            FROM tickets
            ORDER BY created_at DESC
            LIMIT :limit
        """),
            {"limit": limit},
        )
        return [
            {
                "id": row[0],
                "title": row[1][:40] + "..." if len(row[1]) > 40 else row[1],
                "status": row[2],
                "approval": row[3],
                "resolved": row[4],
                "created": str(row[5])[:19],
            }
            for row in result
        ]


def list_tasks(db: DatabaseService, ticket_id: str = None, limit: int = 10) -> list:
    """List recent tasks, optionally filtered by ticket."""
    from sqlalchemy import text

    query = """
        SELECT t.id, t.description, t.status, t.ticket_id, t.created_at
        FROM tasks t
    """
    params = {"limit": limit}

    if ticket_id:
        query += " WHERE t.ticket_id = :ticket_id"
        params["ticket_id"] = ticket_id

    query += " ORDER BY t.created_at DESC LIMIT :limit"

    with db.get_session() as session:
        result = session.execute(text(query), params)
        return [
            {
                "id": row[0],
                "description": row[1][:40] + "..." if len(row[1]) > 40 else row[1],
                "status": row[2],
                "ticket_id": row[3][:8] + "...",
                "created": str(row[4])[:19],
            }
            for row in result
        ]


def get_ticket_history(db: DatabaseService, ticket_id: str) -> list:
    """Get history for a ticket."""
    from sqlalchemy import text

    with db.get_session() as session:
        result = session.execute(
            text("""
            SELECT change_type, change_description, agent_id, changed_at
            FROM ticket_history
            WHERE ticket_id = :ticket_id
            ORDER BY changed_at DESC
            LIMIT 20
        """),
            {"ticket_id": ticket_id},
        )
        return [
            {
                "type": row[0],
                "description": row[1][:50] if row[1] else "",
                "agent": row[2],
                "time": str(row[3])[:19],
            }
            for row in result
        ]


def main():
    parser = argparse.ArgumentParser(description="Demo the OmoiOS flow")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Run command (default behavior)
    run_parser = subparsers.add_parser("run", help="Run a new task from prompt")
    run_parser.add_argument("prompt", help="The task/prompt to execute")
    run_parser.add_argument(
        "--auto-execute", action="store_true", help="Automatically execute the task"
    )
    run_parser.add_argument("--workspace", help="Workspace directory (default: temp)")

    # List tickets command
    list_tickets_parser = subparsers.add_parser("tickets", help="List recent tickets")
    list_tickets_parser.add_argument(
        "--limit", type=int, default=10, help="Number of tickets to show"
    )

    # List tasks command
    list_tasks_parser = subparsers.add_parser("tasks", help="List recent tasks")
    list_tasks_parser.add_argument("--ticket", help="Filter by ticket ID")
    list_tasks_parser.add_argument(
        "--limit", type=int, default=10, help="Number of tasks to show"
    )

    # History command
    history_parser = subparsers.add_parser("history", help="Get ticket history")
    history_parser.add_argument("ticket_id", help="Ticket ID to get history for")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get ticket status")
    status_parser.add_argument("ticket_id", help="Ticket ID to check")

    args = parser.parse_args()

    # Initialize services
    settings = get_app_settings()
    db = DatabaseService(connection_string=settings.database.url)

    # Handle commands
    if args.command == "tickets":
        print("\n📋 Recent Tickets")
        print("=" * 80)
        tickets = list_tickets(db, args.limit)
        if not tickets:
            print("  No tickets found")
        else:
            for t in tickets:
                resolved = "✅" if t["resolved"] else "⏳"
                print(
                    f"  {resolved} {t['id'][:8]}... | {t['title']} | {t['status']} | {t['created']}"
                )
        print()
        return

    if args.command == "tasks":
        print("\n📝 Recent Tasks")
        print("=" * 80)
        tasks = list_tasks(db, args.ticket, args.limit)
        if not tasks:
            print("  No tasks found")
        else:
            for t in tasks:
                status_icon = {
                    "completed": "✅",
                    "running": "🔄",
                    "pending": "⏳",
                    "failed": "❌",
                }.get(t["status"], "❓")
                print(
                    f"  {status_icon} {t['id'][:8]}... | {t['description']} | {t['status']}"
                )
        print()
        return

    if args.command == "history":
        print(f"\n📜 History for Ticket {args.ticket_id[:8]}...")
        print("=" * 80)
        history = get_ticket_history(db, args.ticket_id)
        if not history:
            print("  No history found")
        else:
            for h in history:
                print(f"  [{h['time']}] {h['type']}: {h['description']}")
        print()
        return

    if args.command == "status":
        print("\n🎫 Ticket Status")
        print("=" * 60)
        status = check_ticket_status(db, args.ticket_id)
        for k, v in status.items():
            print(f"  {k}: {v}")
        print()
        return

    # Default: run command (for backward compatibility)
    if args.command is None:
        # Re-parse with legacy format
        parser2 = argparse.ArgumentParser(description="Demo the OmoiOS flow")
        parser2.add_argument("prompt", help="The task/prompt to execute")
        parser2.add_argument(
            "--auto-execute", action="store_true", help="Automatically execute the task"
        )
        parser2.add_argument("--workspace", help="Workspace directory (default: temp)")
        args = parser2.parse_args()

    if args.command == "run" or args.command is None:
        # Run a new task
        queue = TaskQueueService(db)

        print("\n🚀 OmoiOS Demo Flow")
        print("=" * 60)

        # Workspace
        workspace_dir = args.workspace or tempfile.mkdtemp(prefix="omoi_demo_")
        print_info("Workspace", workspace_dir)

        # Step 1: Create ticket from prompt
        print_step(1, "Creating Ticket from Prompt")
        print_info(
            "Prompt", args.prompt[:80] + "..." if len(args.prompt) > 80 else args.prompt
        )

        ticket = create_ticket(db, args.prompt)
        print_info("Ticket ID", ticket["id"])
        print_info("Status", ticket["status"])

        # Step 2: Approve ticket
        print_step(2, "Approving Ticket & Creating Task")

        task = approve_ticket(db, queue, ticket["id"])
        print_info("Task ID", task["id"])
        print_info("Task", task["description"])
        print_info("Status", task["status"])

        # Step 3: Execute (if auto-execute)
        if args.auto_execute:
            print_step(3, "Executing Task with Agent")
            print("  (This may take a minute...)")

            result = execute_task(db, queue, task["id"], workspace_dir)
            print_info("Execution Status", result["status"])
            print_info("Workspace", result["workspace"])

            # Step 4: Check final status
            print_step(4, "Final Ticket Status")
            final = check_ticket_status(db, ticket["id"])
            print_info("Status", final.get("status", "unknown"))
            print_info("Is Resolved", str(final.get("is_resolved", False)))
            if final.get("resolved_at"):
                print_info("Resolved At", final["resolved_at"])
        else:
            print_step(3, "Ready for Execution")
            print("\n  To execute this task, run:")
            print(
                f'  uv run python scripts/demo_flow.py run "{args.prompt}" --auto-execute'
            )
            print("\n  Or manually with:")
            print(f"  Task ID: {task['id']}")
            print(f"  Ticket ID: {ticket['id']}")

        print("\n" + "=" * 60)
        print("✅ Demo complete!")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
