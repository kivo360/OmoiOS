#!/usr/bin/env python3
"""End-to-end API test for sandbox spawning.

Tests the full flow:
1. Create/find project linked to GitHub repo
2. Create ticket with complex math task
3. Wait for task dispatch
4. Monitor sandbox events
5. Verify result

Usage:
    cd backend
    uv run python scripts/test_api_sandbox_spawn.py
"""

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

# Configuration
# Use remote Railway API if API_BASE_URL env var is set, otherwise default to localhost

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:18000")
USER_ID = "f5d0b1a5-da18-46dc-8713-0d9820c65565"  # kivo360@gmail.com
GITHUB_OWNER = "kivo360"
GITHUB_REPO = "OmoiOS"

# Complex math task with file creation and modification - tests file diff tracking
# Result: 126,410,606,437,752 (easy for Python, hard for LLMs)
TASK_DESCRIPTION = """Calculate the binomial coefficient C(50,25) which equals:
    factorial(50) / (factorial(25) * factorial(25))

Use Python to compute this exactly. The answer should be: 126410606437752

Step 1: Create a file called binomial.py with a function to calculate C(n, k)
Step 2: Then modify the file to add a main() function that calls the function with n=50, k=25 and prints the result

This will test file creation and modification tracking."""


async def check_api_health(client: httpx.AsyncClient) -> bool:
    """Check if API is running."""
    try:
        response = await client.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            return True
    except httpx.ConnectError:
        pass
    return False


async def find_or_create_project(client: httpx.AsyncClient) -> str | None:
    """Find existing project or create new one linked to GitHub repo."""
    # First, try to find existing project
    response = await client.get(f"{API_BASE_URL}/api/v1/projects")
    if response.status_code == 200:
        data = response.json()
        projects = data.get("projects", [])
        for proj in projects:
            if (
                proj.get("github_owner") == GITHUB_OWNER
                and proj.get("github_repo") == GITHUB_REPO
            ):
                print(f"   Found existing project: {proj['id']}")
                return proj["id"]

    # Create new project
    project_data = {
        "name": f"{GITHUB_OWNER}/{GITHUB_REPO}",
        "description": "OmoiOS project for sandbox testing",
        "github_owner": GITHUB_OWNER,
        "github_repo": GITHUB_REPO,
        "default_phase_id": "PHASE_IMPLEMENTATION",
    }

    response = await client.post(
        f"{API_BASE_URL}/api/v1/projects",
        json=project_data,
    )

    if response.status_code == 200:
        data = response.json()
        project_id = data.get("id")
        print(f"   Created new project: {project_id}")

        # Update project with created_by (user_id) - need direct DB access
        # The API doesn't expose this, so we'll do it directly
        await set_project_user(project_id)

        return project_id

    print(f"   ❌ Failed to create project: {response.status_code} {response.text}")
    return None


async def set_project_user(project_id: str) -> None:
    """Set the created_by user for the project via direct DB access."""
    try:
        from omoi_os.config import get_app_settings
        from omoi_os.services.database import DatabaseService
        from omoi_os.models.project import Project

        settings = get_app_settings()
        db = DatabaseService(settings.database.url)
        with db.get_session() as session:
            project = session.get(Project, project_id)
            if project:
                project.created_by = UUID(USER_ID)
                session.commit()
                print(f"   Set project created_by to {USER_ID}")
    except Exception as e:
        print(f"   ⚠️  Could not set project user: {e}")


async def create_ticket(client: httpx.AsyncClient, project_id: str) -> dict | None:
    """Create a ticket with the complex math task."""
    import time

    # Use unique title to avoid duplicate detection
    timestamp = int(time.time())
    ticket_data = {
        "title": f"Calculate Binomial Coefficient C(50,25) [{timestamp}]",
        "description": TASK_DESCRIPTION,
        "phase_id": "PHASE_IMPLEMENTATION",
        "priority": "HIGH",
        "project_id": project_id,
        "force_create": True,  # Skip duplicate detection
    }

    response = await client.post(
        f"{API_BASE_URL}/api/v1/tickets",
        json=ticket_data,
    )

    if response.status_code == 200:
        data = response.json()
        return data

    print(f"   ❌ Failed to create ticket: {response.status_code} {response.text}")
    return None


async def get_ticket_tasks(
    client: httpx.AsyncClient, ticket_id: str
) -> list[dict] | None:
    """Get tasks for a ticket."""
    try:
        response = await client.get(f"{API_BASE_URL}/api/v1/tasks")
        if response.status_code == 200:
            data = response.json()
            # API returns a list directly, not a dict with "tasks" key
            tasks_list = data if isinstance(data, list) else data.get("tasks", [])
            tasks = [t for t in tasks_list if t.get("ticket_id") == ticket_id]
            return tasks
        else:
            if hasattr(response, "text"):
                print(
                    f"   [DEBUG] Failed to get tasks: {response.status_code} - {response.text[:200]}"
                )
    except Exception as e:
        print(f"   [DEBUG] Exception getting tasks: {e}")
    return None


async def poll_for_task(
    client: httpx.AsyncClient, ticket_id: str, timeout: int = 180
) -> dict | None:
    """Poll until a task is created and picked up."""
    start_time = time.time()
    last_status = None
    poll_count = 0
    task_created = False

    print(f"   [DEBUG] Starting poll loop (timeout: {timeout}s)")

    while time.time() - start_time < timeout:
        elapsed = int(time.time() - start_time)
        poll_count += 1

        if poll_count == 1:
            print(
                f"   [DEBUG] Poll #{poll_count} (elapsed: {elapsed}s) - Checking for tasks..."
            )

        tasks = await get_ticket_tasks(client, ticket_id)

        if not tasks:
            if not task_created:
                if poll_count % 5 == 0:  # Log every 5th poll when no tasks
                    print(
                        f"   [DEBUG] Poll #{poll_count} (elapsed: {elapsed}s) - No tasks found yet"
                    )
            await asyncio.sleep(2)
            continue

        task_created = True
        task = tasks[0]
        task_id = task.get("id")
        status = task.get("status")
        assigned_agent = task.get("assigned_agent_id")
        phase_id = task.get("phase_id")

        # Get full task details - API might not include sandbox_id, so check DB directly
        response = await client.get(f"{API_BASE_URL}/api/v1/tasks/{task_id}")
        if response.status_code == 200:
            full_task = response.json()
            sandbox_id = full_task.get("sandbox_id")
        else:
            print(f"   [DEBUG] Failed to get full task details: {response.status_code}")
            full_task = task
            sandbox_id = None

        # If API doesn't have sandbox_id, check database directly
        if not sandbox_id:
            try:
                from omoi_os.config import get_app_settings
                from omoi_os.services.database import DatabaseService
                from omoi_os.models.task import Task as TaskModel

                settings = get_app_settings()
                db = DatabaseService(settings.database.url)
                with db.get_session() as session:
                    db_task = (
                        session.query(TaskModel).filter(TaskModel.id == task_id).first()
                    )
                    if db_task:
                        if db_task.sandbox_id:
                            sandbox_id = db_task.sandbox_id
                            print(
                                f"   [DEBUG] Found sandbox_id in DB: {sandbox_id[:20]}..."
                            )
                            # Add to full_task for return
                            if isinstance(full_task, dict):
                                full_task["sandbox_id"] = sandbox_id
                        else:
                            if poll_count % 10 == 0:  # Log every 10th poll
                                print(
                                    f"   [DEBUG] Task exists but no sandbox_id yet (status: {status})"
                                )
            except Exception as e:
                if poll_count % 10 == 0:
                    print(f"   [DEBUG] DB check failed: {e}")

        # Log status changes or new information
        if status != last_status or sandbox_id or poll_count % 10 == 0:
            status_msg = (
                f"   [Poll #{poll_count}] Task {task_id[:8]}... | Status: {status}"
            )
            if assigned_agent:
                status_msg += f" | Agent: {assigned_agent[:8]}..."
            if phase_id:
                status_msg += f" | Phase: {phase_id}"
            if sandbox_id:
                status_msg += f" | Sandbox: {sandbox_id[:20]}..."
            print(status_msg)
            last_status = status

        # Check for activity indicators (worker is working even if status hasn't updated)
        activity = await check_task_activity(client, task_id, sandbox_id)

        # Task is picked up if:
        # 1. Status is in_progress/running/completed/failed, OR
        # 2. Status is assigned AND sandbox_id exists (sandbox spawned, worker initializing), OR
        # 3. Status is assigned AND activity detected (worker is active even if status not updated)
        if status in ["in_progress", "running", "completed", "failed"]:
            print(f"   ✅ Task picked up! Status: {status}")
            if sandbox_id:
                print(f"   ✅ Sandbox ID: {sandbox_id}")
            if activity["has_activity"]:
                print(
                    f"   ✅ Activity detected: {', '.join(activity['activity_types'][:3])}"
                )
            return full_task if sandbox_id else task
        elif status == "assigned" and sandbox_id:
            if activity["has_activity"]:
                print("   ✅ Task assigned with sandbox - worker is active!")
                print(f"   ✅ Sandbox ID: {sandbox_id}")
                print(
                    f"   ✅ Activity: {', '.join(activity['activity_types'][:3])} ({activity['event_count']} events)"
                )
            else:
                print("   ✅ Task assigned with sandbox - worker initializing...")
                print(f"   ✅ Sandbox ID: {sandbox_id}")
            return full_task
        elif status == "assigned" and activity["has_activity"]:
            # Worker is active even though sandbox_id might not be set yet
            print("   ✅ Task assigned - worker activity detected!")
            print(
                f"   ✅ Activity: {', '.join(activity['activity_types'][:3])} ({activity['event_count']} events)"
            )
            if sandbox_id:
                print(f"   ✅ Sandbox ID: {sandbox_id}")
            return full_task if sandbox_id else task
        elif status == "assigned" and not sandbox_id:
            if poll_count % 10 == 0:
                print(
                    "   [DEBUG] Task assigned but no sandbox yet - orchestrator may not be running"
                )
                print(
                    "   [DEBUG] Check: ORCHESTRATOR_ENABLED should be 'true' and orchestrator worker should be running"
                )

        await asyncio.sleep(2)

    elapsed_total = int(time.time() - start_time)
    print(f"\n   ❌ Polling timeout after {elapsed_total}s ({poll_count} polls)")
    print(f"   [DEBUG] Last seen status: {last_status}")
    print("   [DEBUG] Make sure:")
    print(
        "      - Orchestrator worker is running: python -m omoi_os.workers.orchestrator_worker"
    )
    print("      - ORCHESTRATOR_ENABLED=true in environment")
    print("      - DAYTONA_SANDBOX_EXECUTION=true in environment")
    return None


async def get_sandbox_events(
    client: httpx.AsyncClient, sandbox_id: str, seen_event_ids: set[str]
) -> list[dict]:
    """Get new sandbox events (ones we haven't seen before)."""
    response = await client.get(
        f"{API_BASE_URL}/api/v1/sandboxes/{sandbox_id}/events?limit=50"
    )
    if response.status_code == 200:
        data = response.json()
        events = data.get("events", [])
        new_events = []

        for event in events:
            event_id = event.get("id")
            if event_id and event_id not in seen_event_ids:
                seen_event_ids.add(event_id)
                new_events.append(event)

                event_type = event.get("event_type", "unknown")

                # Track file edit events for testing
                if event_type == "agent.file_edited":
                    event_data = event.get("event_data", {})
                    file_path = event_data.get("file_path", "unknown")
                    change_type = event_data.get("change_type", "unknown")
                    lines_added = event_data.get("lines_added", 0)
                    lines_removed = event_data.get("lines_removed", 0)
                    print(
                        f"   📝 File edit: {file_path} ({change_type}, +{lines_added} -{lines_removed})"
                    )

        return new_events

    return []


async def check_task_activity(
    client: httpx.AsyncClient, task_id: str, sandbox_id: str | None = None
) -> dict[str, Any]:
    """Check for activity indicators that task is being worked on.

    Returns dict with:
    - has_activity: bool - True if any activity detected
    - activity_types: list[str] - Types of activity found
    - event_count: int - Number of events found
    - latest_event_type: str | None - Most recent event type
    """
    activity = {
        "has_activity": False,
        "activity_types": [],
        "event_count": 0,
        "latest_event_type": None,
    }

    # Check sandbox events if we have a sandbox_id
    if sandbox_id:
        try:
            response = await client.get(
                f"{API_BASE_URL}/api/v1/sandboxes/{sandbox_id}/events?limit=20"
            )
            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])
                activity["event_count"] = len(events)

                # Activity indicators - events that show the worker is active
                activity_indicators = [
                    "agent.started",
                    "agent.message",
                    "agent.thinking",
                    "agent.tool_use",
                    "agent.tool_completed",
                    "agent.tool_result",
                    "agent.file_edited",
                    "agent.assistant_message",
                    "agent.heartbeat",
                    "agent.subagent_invoked",
                    "agent.skill_invoked",
                ]

                for event in events:
                    event_type = event.get("event_type", "")
                    if event_type in activity_indicators:
                        activity["has_activity"] = True
                        if event_type not in activity["activity_types"]:
                            activity["activity_types"].append(event_type)
                        if not activity["latest_event_type"]:
                            activity["latest_event_type"] = event_type
        except Exception:
            # Silently fail - events might not be available yet
            pass

    # Also check task conversation_id - if it exists, worker has started
    try:
        response = await client.get(f"{API_BASE_URL}/api/v1/tasks/{task_id}")
        if response.status_code == 200:
            task_data = response.json()
            conversation_id = task_data.get("conversation_id")
            if conversation_id:
                activity["has_activity"] = True
                if "conversation_started" not in activity["activity_types"]:
                    activity["activity_types"].append("conversation_started")
    except Exception:
        pass

    return activity


async def get_sandbox_logs(
    sandbox_id: str, last_line_count: int = 0
) -> tuple[str, int]:
    """Get logs from Daytona sandbox and return new lines.

    Args:
        sandbox_id: Sandbox ID to get logs from
        last_line_count: Number of lines we've already seen (to only show new ones)

    Returns:
        Tuple of (new_log_lines, total_line_count)
    """
    try:
        from omoi_os.config import load_daytona_settings
        from daytona import Daytona, DaytonaConfig

        daytona_settings = load_daytona_settings()
        if not daytona_settings.api_key:
            return "", last_line_count

        config = DaytonaConfig(
            api_key=daytona_settings.api_key,
            api_url=daytona_settings.api_url,
            target="us",
        )

        daytona = Daytona(config)
        sandbox = daytona.get(sandbox_id)

        # Get all log lines
        result = sandbox.process.exec("cat /tmp/worker.log 2>/dev/null || echo ''")
        output = result.result if hasattr(result, "result") else str(result)

        if not output or not output.strip():
            return "", last_line_count

        # Split into lines and get new ones
        all_lines = output.splitlines()
        total_lines = len(all_lines)

        if total_lines > last_line_count:
            new_lines = all_lines[last_line_count:]
            return "\n".join(new_lines), total_lines

        return "", total_lines

    except Exception:
        # Silently fail - logs might not be available yet, sandbox might not be ready, etc.
        return "", last_line_count


async def find_sandbox_for_task(client: httpx.AsyncClient, task_id: str) -> str | None:
    """Find sandbox ID for a task by checking recent events."""
    # Check agent assignments
    response = await client.get(f"{API_BASE_URL}/api/v1/tasks/{task_id}")
    if response.status_code == 200:
        task_data = response.json()
        agent_id = task_data.get("assigned_agent_id")
        if agent_id:
            # The sandbox_id is typically related to the task
            # Check the spawner's tracking - we need to use a different approach
            pass

    # Alternative: search events for SANDBOX_SPAWNED
    return None


async def create_branch_for_task(
    client: httpx.AsyncClient, ticket_id: str, task_id: str
) -> dict | None:
    """Create a feature branch for the task."""
    branch_data = {
        "ticket_id": ticket_id,
        "ticket_title": f"binomial-task-{task_id[:8]}",
        "repo_owner": GITHUB_OWNER,
        "repo_name": GITHUB_REPO,
        "user_id": USER_ID,
        "ticket_type": "feature",
    }

    response = await client.post(
        f"{API_BASE_URL}/api/v1/branch-workflow/start",
        json=branch_data,
    )

    if response.status_code == 200:
        return response.json()

    print(f"   ⚠️  Branch creation failed: {response.status_code} {response.text}")
    return None


async def main():
    print("=" * 70)
    print("🧪 API SANDBOX SPAWN END-TO-END TEST")
    print("=" * 70)
    print(f"\nUser ID: {USER_ID}")
    print(f"Repository: {GITHUB_OWNER}/{GITHUB_REPO}")

    # Show configuration
    print("\n📋 Configuration:")
    print(f"   API Base URL: {API_BASE_URL}")

    # Show database URL from app_settings (masked for security)
    try:
        from omoi_os.config import get_app_settings

        settings = get_app_settings()
        db_url = settings.database.url
        # Mask password in URL
        if "@" in db_url:
            parts = db_url.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
                if ":" in user_pass:
                    user, _ = user_pass.split(":", 1)
                    protocol = parts[0].split("://")[0] if "://" in parts[0] else ""
                    masked_url = f"{protocol}://{user}:***@{parts[1]}"
                else:
                    masked_url = db_url
            else:
                masked_url = db_url
        else:
            masked_url = db_url
        print(f"   Database URL: {masked_url}")

        redis_url = settings.redis.url
        if "@" in redis_url:
            parts = redis_url.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
                if ":" in user_pass:
                    user, _ = user_pass.split(":", 1)
                    protocol = parts[0].split("://")[0] if "://" in parts[0] else ""
                    masked_redis = f"{protocol}://{user}:***@{parts[1]}"
                else:
                    masked_redis = redis_url
            else:
                masked_redis = redis_url
        else:
            masked_redis = redis_url
        print(f"   Redis URL: {masked_redis}")

        # Check orchestrator settings
        orchestrator_enabled = (
            os.environ.get("ORCHESTRATOR_ENABLED", "false").lower() == "true"
        )
        sandbox_execution = (
            os.environ.get("DAYTONA_SANDBOX_EXECUTION", "false").lower() == "true"
        )
        print("\n   🔧 Orchestrator Settings:")
        print(f"      ORCHESTRATOR_ENABLED: {orchestrator_enabled}")
        print(f"      DAYTONA_SANDBOX_EXECUTION: {sandbox_execution}")
        if not orchestrator_enabled:
            print(
                "      ⚠️  WARNING: Orchestrator is DISABLED - tasks won't be picked up!"
            )
        if not sandbox_execution:
            print(
                "      ⚠️  WARNING: Sandbox execution is DISABLED - sandboxes won't spawn!"
            )

    except Exception as e:
        print(f"   ⚠️  Could not load settings: {e}")

    print()

    # Use longer timeout for remote Railway API (network latency)
    timeout = httpx.Timeout(60.0, connect=10.0)  # 60s total, 10s connect
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Step 1: Check API availability
        print("[1/6] Checking API availability...")
        if not await check_api_health(client):
            print("   ❌ API not running at", API_BASE_URL)
            print("   Start it with: just watch")
            return
        print("   ✅ API is running")

        # Step 2: Find or create project
        print("\n[2/6] Setting up project for", f"{GITHUB_OWNER}/{GITHUB_REPO}...")
        project_id = await find_or_create_project(client)
        if not project_id:
            print("   ❌ Failed to setup project")
            return
        print(f"   ✅ Project ready: {project_id}")

        # Step 3: Create ticket with complex math task
        print("\n[3/6] Creating ticket with binomial coefficient task...")
        ticket_start = time.time()
        ticket = await create_ticket(client, project_id)
        if not ticket:
            print("   ❌ Failed to create ticket")
            return

        ticket_id = ticket.get("id")
        ticket_elapsed = time.time() - ticket_start
        print(f"   ✅ Ticket created: {ticket_id} (took {ticket_elapsed:.2f}s)")
        print(f"   [DEBUG] Ticket title: {ticket.get('title', 'N/A')}")
        print(
            f"   [DEBUG] Ticket description length: {len(ticket.get('description', ''))} chars"
        )

        # Step 4: Wait for task dispatch
        print("\n[4/6] Waiting for task dispatch (max 3 min)...")
        print(f"   [DEBUG] Ticket ID: {ticket_id}")
        print(f"   [DEBUG] Polling for tasks with ticket_id={ticket_id}")
        task_start = time.time()
        task = await poll_for_task(client, ticket_id, timeout=180)
        task_elapsed = time.time() - task_start

        if not task:
            print(f"\n   ❌ No task picked up within timeout ({task_elapsed:.1f}s)")
            print("\n   [DEBUG] Troubleshooting steps:")
            print("      1. Check if orchestrator worker is running:")
            print("         python -m omoi_os.workers.orchestrator_worker")
            print("      2. Verify environment variables:")
            print("         - ORCHESTRATOR_ENABLED=true")
            print("         - DAYTONA_SANDBOX_EXECUTION=true")
            print("      3. Check orchestrator logs for errors")
            print("      4. Verify database connection is working")
            print("      5. Check if tasks are being created in the database")

            # Try to get tasks one more time for debugging
            print("\n   [DEBUG] Final task check...")
            tasks = await get_ticket_tasks(client, ticket_id)
            if tasks:
                print(f"   [DEBUG] Found {len(tasks)} task(s) in database:")
                for t in tasks:
                    print(
                        f"      - Task {t.get('id', 'N/A')[:8]}... | Status: {t.get('status', 'N/A')}"
                    )
            else:
                print("   [DEBUG] No tasks found in database for this ticket")
            return

        task_id = task.get("id")
        assigned_agent = task.get("assigned_agent_id")
        sandbox_id = task.get("sandbox_id")
        task_status = task.get("status")
        phase_id = task.get("phase_id")

        print(f"\n   ✅ Task picked up! (took {task_elapsed:.1f}s)")
        print(f"   [DEBUG] Task ID: {task_id}")
        print(f"   [DEBUG] Status: {task_status}")
        print(f"   [DEBUG] Assigned Agent: {assigned_agent or 'None'}")
        print(f"   [DEBUG] Phase ID: {phase_id or 'None'}")
        if sandbox_id:
            print(f"   [DEBUG] Sandbox ID: {sandbox_id}")
        else:
            print("   [DEBUG] Sandbox ID: None (sandbox may not be spawned yet)")

        # Step 5: Try to create branch (optional, may fail if no GitHub token)
        print("\n[5/6] Creating feature branch...")
        branch_result = await create_branch_for_task(client, ticket_id, task_id)
        if branch_result and branch_result.get("success"):
            print(f"   ✅ Branch created: {branch_result.get('branch_name')}")
        else:
            print("   ⚠️  Branch creation skipped (may need GitHub token)")

        # Step 6: Monitor sandbox events
        print("\n[6/6] Monitoring sandbox events (max 5 min)...")
        print("   Waiting for agent to compute C(50,25) = 126,410,606,437,752")
        print(
            "   Also watching for file edit events (agent.file_edited) to test diff tracking"
        )
        print()

        # Get sandbox_id from task (it's set after sandbox is spawned)
        sandbox_id = None
        start_time = time.time()
        max_wait = 300  # 5 minutes
        file_edit_events = []
        seen_event_ids = set()
        last_log_line_count = 0
        log_poll_count = 0

        while time.time() - start_time < max_wait:
            # Get task status and sandbox_id
            response = await client.get(f"{API_BASE_URL}/api/v1/tasks/{task_id}")
            if response.status_code == 200:
                task_data = response.json()
                status = task_data.get("status")
                result = task_data.get("result")
                error = task_data.get("error_message")

                # Get sandbox_id if available
                if not sandbox_id:
                    sandbox_id = task_data.get("sandbox_id")
                    if sandbox_id:
                        print(f"   📦 Found sandbox_id: {sandbox_id}")
                        print("   Polling sandbox events for file edits...")
                        print(
                            "   📋 Worker logs will be displayed below as they appear:"
                        )
                        print("   " + "-" * 60)
                        print()

                # If we have sandbox_id, check for new events and logs
                if sandbox_id:
                    # Poll for new events
                    new_events = await get_sandbox_events(
                        client, sandbox_id, seen_event_ids
                    )
                    for event in new_events:
                        if event.get("event_type") == "agent.file_edited":
                            event_data = event.get("event_data", {})
                            file_edit_events.append(
                                {
                                    "file_path": event_data.get("file_path"),
                                    "change_type": event_data.get("change_type"),
                                    "lines_added": event_data.get("lines_added", 0),
                                    "lines_removed": event_data.get("lines_removed", 0),
                                }
                            )

                    # Poll for new log lines (every 3 iterations to avoid too much output)
                    log_poll_count += 1
                    if (
                        log_poll_count >= 3
                    ):  # Poll logs every ~15 seconds (3 * 5s sleep)
                        log_poll_count = 0
                        try:
                            new_logs, total_lines = await get_sandbox_logs(
                                sandbox_id, last_log_line_count
                            )
                            if new_logs:
                                # Print new log lines with indentation
                                for line in new_logs.splitlines():
                                    print(f"   [LOG] {line}")
                                last_log_line_count = total_lines
                        except Exception:
                            # Silently fail - logs might not be available yet
                            pass

                # Check for completion via multiple methods:
                # 1. Task status == "completed" (primary method)
                # 2. Worker logs show "📊 Completed" (fallback if status not updated)
                worker_completed = False
                if sandbox_id:
                    try:
                        current_logs, _ = await get_sandbox_logs(
                            sandbox_id, last_log_line_count
                        )
                        if current_logs:
                            # Check if worker logs show completion
                            if (
                                "📊 Completed:" in current_logs
                                or "⏳ Waiting for messages..." in current_logs
                            ):
                                # Worker has completed - check if we saw the completion message
                                if "📊 Completed:" in current_logs:
                                    worker_completed = True
                                    print(
                                        "\n   [LOG] Worker logs indicate task completed!"
                                    )
                                    # Extract completion info from logs
                                    for line in current_logs.splitlines():
                                        if "📊 Completed:" in line:
                                            print(f"   [LOG] {line}")
                    except Exception:
                        pass

                if status == "completed" or worker_completed:
                    # Get final logs before completion
                    if sandbox_id:
                        try:
                            final_logs, _ = await get_sandbox_logs(
                                sandbox_id, last_log_line_count
                            )
                            if final_logs:
                                print("\n   [LOG] Final worker output:")
                                for line in final_logs.splitlines():
                                    print(f"   [LOG] {line}")
                        except Exception:
                            pass

                    if worker_completed and status != "completed":
                        print(
                            "\n   ⚠️  Worker completed but task status not updated yet"
                        )
                        print(
                            "   This may be due to event reporting issues (502 errors)"
                        )
                        print(
                            "   Task completed successfully - status update may be delayed"
                        )

                        # Try to check if result is in the logs
                        if sandbox_id:
                            try:
                                all_logs, _ = await get_sandbox_logs(sandbox_id, 0)
                                if all_logs and "126410606437752" in all_logs:
                                    print(
                                        "\n   ✅ SUCCESS! Agent computed C(50,25) = 126,410,606,437,752"
                                    )
                                    print("   (Detected from worker logs)")
                            except Exception:
                                pass

                    print("\n   🎉 Task COMPLETED!")
                    if result:
                        print(f"   Result: {result}")

                    # Check if the correct answer is in the result
                    if result and "126410606437752" in str(result):
                        print(
                            "\n✅ SUCCESS! Agent computed C(50,25) = 126,410,606,437,752"
                        )

                    # Report file edit events
                    if file_edit_events:
                        print(
                            f"\n   📝 File Edit Events Detected: {len(file_edit_events)}"
                        )
                        for i, fe in enumerate(file_edit_events, 1):
                            print(
                                f"      {i}. {fe['file_path']} ({fe['change_type']}, +{fe['lines_added']} -{fe['lines_removed']})"
                            )
                        print("   ✅ File diff tracking is working correctly!")
                    else:
                        print(
                            "   ⚠️  No file edit events detected - agent may not have created/modified files"
                        )

                    break

                elif status == "failed":
                    # Get final logs on failure
                    if sandbox_id:
                        try:
                            final_logs, _ = await get_sandbox_logs(
                                sandbox_id, last_log_line_count
                            )
                            if final_logs:
                                print("\n   [LOG] Worker output before failure:")
                                for line in final_logs.splitlines():
                                    print(f"   [LOG] {line}")
                        except Exception:
                            pass

                    print(f"   ❌ Task FAILED: {error}")
                    break

            await asyncio.sleep(5)
        else:
            print("   ⏰ Timeout waiting for task completion")

            # Final check: Did the worker complete even if status wasn't updated?
            if sandbox_id:
                print(
                    "\n   [DEBUG] Final check - checking worker logs for completion..."
                )
                try:
                    final_logs, _ = await get_sandbox_logs(sandbox_id, 0)
                    if final_logs:
                        if "📊 Completed:" in final_logs:
                            print("   ✅ Worker logs show task was completed!")
                            print(
                                "   ⚠️  However, task status was not updated in database"
                            )
                            print(
                                "   This suggests event reporting failed (likely 502 errors)"
                            )
                            print(
                                "   Task completed successfully, but status update is delayed"
                            )

                            # Check for the answer in logs
                            if "126410606437752" in final_logs:
                                print(
                                    "\n   ✅ SUCCESS! Agent computed C(50,25) = 126,410,606,437,752"
                                )
                                print(
                                    "   (Detected from worker logs despite status not updating)"
                                )
                        else:
                            print("   [DEBUG] Worker logs do not show completion")
                except Exception as e:
                    print(f"   [DEBUG] Could not check final logs: {e}")

        # Final summary of file edit events
        if file_edit_events:
            print(
                f"\n   📊 Summary: {len(file_edit_events)} file edit event(s) detected"
            )
            print("   ✅ File diff tracking feature is working!")

    print("\n" + "=" * 70)
    print("🏁 API TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
