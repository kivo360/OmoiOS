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
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

# Configuration
API_BASE_URL = "http://localhost:18000"
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
    response = await client.get(f"{API_BASE_URL}/api/v1/tasks")
    if response.status_code == 200:
        data = response.json()
        # API returns a list directly, not a dict with "tasks" key
        tasks_list = data if isinstance(data, list) else data.get("tasks", [])
        tasks = [t for t in tasks_list if t.get("ticket_id") == ticket_id]
        return tasks
    return None


async def poll_for_task(
    client: httpx.AsyncClient, ticket_id: str, timeout: int = 120
) -> dict | None:
    """Poll until a task is created and picked up."""
    start_time = time.time()
    last_status = None

    while time.time() - start_time < timeout:
        tasks = await get_ticket_tasks(client, ticket_id)
        if tasks:
            task = tasks[0]
            status = task.get("status")
            if status != last_status:
                print(f"   Task {task['id'][:8]}... status: {status}")
                last_status = status

            if status in ["in_progress", "running", "completed", "failed"]:
                return task

        await asyncio.sleep(2)

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
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
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
        ticket = await create_ticket(client, project_id)
        if not ticket:
            print("   ❌ Failed to create ticket")
            return

        ticket_id = ticket.get("id")
        print(f"   ✅ Ticket created: {ticket_id}")

        # Step 4: Wait for task dispatch
        print("\n[4/6] Waiting for task dispatch (max 2 min)...")
        task = await poll_for_task(client, ticket_id, timeout=120)
        if not task:
            print("   ❌ No task picked up within timeout")
            print(
                "   Make sure DAYTONA_SANDBOX_EXECUTION=true and orchestrator is running"
            )
            return

        task_id = task.get("id")
        assigned_agent = task.get("assigned_agent_id")
        print(f"   ✅ Task assigned: {task_id[:8]}...")
        print(f"   Agent: {assigned_agent}")

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
                        print()

                # If we have sandbox_id, check for new events
                if sandbox_id:
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

                if status == "completed":
                    print("   🎉 Task COMPLETED!")
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
                    print(f"   ❌ Task FAILED: {error}")
                    break

            await asyncio.sleep(5)
        else:
            print("   ⏰ Timeout waiting for task completion")

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
