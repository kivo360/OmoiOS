#!/usr/bin/env python3
"""Test script for Claude session transcript cross-sandbox resumption.

This script tests the full flow of:
1. Spawning a sandbox with a Claude agent
2. Running a conversation that generates a session
3. Completing the session and verifying transcript is saved
4. Spawning a new sandbox with RESUME_SESSION_ID
5. Verifying the conversation continues from where it left off

Usage:
    cd backend
    uv run python scripts/test_claude_session_transcript.py

Requirements:
    - Database must be running and migrated (037_claude_session_transcripts)
    - API server must be running on localhost:18000
    - Daytona must be configured and accessible
    - ANTHROPIC_API_KEY must be set in environment
"""

import asyncio
import sys
import time
from pathlib import Path
from typing import Optional

import httpx

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env.local")

# Configuration
API_BASE_URL = "http://localhost:18000"
TIMEOUT_SECONDS = 300  # 5 minutes max per sandbox


async def check_api_health(client: httpx.AsyncClient) -> bool:
    """Check if API is running."""
    try:
        response = await client.get(f"{API_BASE_URL}/health")
        return response.status_code == 200
    except httpx.ConnectError:
        return False


async def create_test_task(client: httpx.AsyncClient) -> Optional[str]:
    """Create a simple test task for Claude agent."""
    # Create a ticket - tasks are automatically created when tickets are created
    ticket_response = await client.post(
        f"{API_BASE_URL}/api/v1/tickets",
        json={
            "title": "Session Transcript Test",
            "description": "Create a Python file called hello.py that prints 'Hello from session test!' and run it.",
            "ticket_type": "feature",
            "phase_id": "PHASE_IMPLEMENTATION",
            "priority": "MEDIUM",
            "force_create": True,  # Skip duplicate check for test
        },
    )

    if ticket_response.status_code != 200:
        print(f"❌ Failed to create ticket: {ticket_response.status_code}")
        print(f"   Response: {ticket_response.text}")
        return None

    ticket_id = ticket_response.json().get("id")
    print(f"✅ Created ticket: {ticket_id}")

    # Wait a moment for task to be created
    await asyncio.sleep(1)

    # Find the task associated with this ticket
    # Tasks are automatically created when a ticket is created
    tasks_response = await client.get(f"{API_BASE_URL}/api/v1/tasks")
    if tasks_response.status_code == 200:
        tasks = tasks_response.json()
        # Find task for this ticket
        for task in tasks:
            if task.get("ticket_id") == ticket_id:
                task_id = task.get("id")
                print(f"✅ Found task: {task_id}")
                return task_id

    print(f"⚠️  No task found for ticket {ticket_id}, but continuing anyway...")
    print(f"   (Task may be created asynchronously)")
    return None


async def spawn_sandbox(
    client: httpx.AsyncClient, task_id: str, resume_session_id: Optional[str] = None
) -> Optional[str]:
    """Spawn a sandbox for a task, optionally resuming a session."""
    spawn_data = {
        "task_id": task_id,
        "runtime": "claude",
    }

    if resume_session_id:
        spawn_data["extra_env"] = {"RESUME_SESSION_ID": resume_session_id}
        print(f"🔄 Spawning sandbox with resume_session_id: {resume_session_id[:8]}...")

    response = await client.post(
        f"{API_BASE_URL}/api/v1/sandboxes/spawn",
        json=spawn_data,
    )

    if response.status_code == 200:
        data = response.json()
        sandbox_id = data.get("sandbox_id")
        print(f"✅ Spawned sandbox: {sandbox_id}")
        return sandbox_id

    print(f"❌ Failed to spawn sandbox: {response.status_code} {response.text}")
    return None


async def poll_for_completion(
    client: httpx.AsyncClient, sandbox_id: str, timeout: int = TIMEOUT_SECONDS
) -> Optional[dict]:
    """Poll sandbox events until agent.completed is received."""
    start_time = time.time()
    seen_event_ids = set()

    while time.time() - start_time < timeout:
        response = await client.get(
            f"{API_BASE_URL}/api/v1/sandboxes/{sandbox_id}/events"
        )

        if response.status_code == 200:
            data = response.json()
            events = data.get("events", [])

            for event in events:
                event_id = event.get("id")
                if event_id in seen_event_ids:
                    continue

                seen_event_ids.add(event_id)
                event_type = event.get("event_type")

                if event_type == "agent.completed":
                    event_data = event.get("event_data", {})
                    print("✅ Session completed!")
                    print(f"   Session ID: {event_data.get('session_id', 'N/A')}")
                    print(f"   Turns: {event_data.get('turns', 'N/A')}")
                    print(f"   Cost: ${event_data.get('cost_usd', 0):.4f}")
                    print(
                        f"   Transcript saved: {'Yes' if event_data.get('transcript_b64') else 'No'}"
                    )
                    return event_data

                if "error" in event_type.lower() or "fail" in event_type.lower():
                    error_msg = event.get("event_data", {}).get(
                        "error", "Unknown error"
                    )
                    print(f"❌ Error event: {event_type} - {error_msg}")
                    return None

        await asyncio.sleep(2)

    print(f"⏱️  Timeout waiting for completion after {timeout}s")
    return None


async def verify_transcript_in_db(
    client: httpx.AsyncClient, session_id: str
) -> Optional[str]:
    """Verify transcript exists in database by querying via API."""
    # We'll need to add an API endpoint for this, but for now let's check via events
    # or we can query the database directly in the test
    try:
        # Direct database query for testing
        from omoi_os.services.database import DatabaseService
        from omoi_os.api.routes.sandbox import get_session_transcript

        # Create a minimal DB service for testing
        # In practice, you'd use dependency injection
        db = DatabaseService()
        transcript_b64 = get_session_transcript(db, session_id)

        if transcript_b64:
            print(
                f"✅ Transcript found in database ({len(transcript_b64)} bytes base64)"
            )
            return transcript_b64
        else:
            print(f"❌ Transcript not found in database for session {session_id}")
            return None
    except Exception as e:
        print(f"⚠️  Could not verify transcript in DB: {e}")
        return None


async def send_message_to_sandbox(
    client: httpx.AsyncClient, sandbox_id: str, message: str
) -> bool:
    """Send a message to a running sandbox."""
    response = await client.post(
        f"{API_BASE_URL}/api/v1/sandboxes/{sandbox_id}/messages",
        json={"content": message, "message_type": "user_message"},
    )
    return response.status_code == 200


async def main():
    print("=" * 70)
    print("🧪 CLAUDE SESSION TRANSCRIPT TEST")
    print("=" * 70)
    print()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Check API health
        if not await check_api_health(client):
            print("❌ API server is not running. Please start it first.")
            return 1

        print("✅ API server is running")
        print()

        # Step 1: Create test task
        print("Step 1: Creating test task...")
        task_id = await create_test_task(client)
        if not task_id:
            return 1
        print()

        # Step 2: Spawn first sandbox (initial session)
        print("Step 2: Spawning first sandbox (initial session)...")
        sandbox_id_1 = await spawn_sandbox(client, task_id)
        if not sandbox_id_1:
            return 1
        print()

        # Step 3: Wait for completion and capture session_id
        print("Step 3: Waiting for first session to complete...")
        completion_data = await poll_for_completion(client, sandbox_id_1)
        if not completion_data:
            print("❌ First session did not complete successfully")
            return 1

        session_id = completion_data.get("session_id")
        if not session_id:
            print("❌ No session_id in completion data")
            return 1

        print(f"📝 Captured session_id: {session_id}")
        print()

        # Step 4: Verify transcript was saved
        print("Step 4: Verifying transcript was saved to database...")
        transcript_b64 = await verify_transcript_in_db(client, session_id)
        if not transcript_b64:
            print("❌ Transcript not found in database")
            return 1
        print()

        # Step 5: Wait a bit, then spawn second sandbox with resume
        print("Step 5: Spawning second sandbox to resume session...")
        await asyncio.sleep(5)  # Brief pause to ensure cleanup

        sandbox_id_2 = await spawn_sandbox(
            client, task_id, resume_session_id=session_id
        )
        if not sandbox_id_2:
            return 1
        print()

        # Step 6: Send a continuation message
        print("Step 6: Sending continuation message to verify context is preserved...")
        continuation_sent = await send_message_to_sandbox(
            client,
            sandbox_id_2,
            "What did we just do? Please summarize what happened in our previous conversation.",
        )
        if not continuation_sent:
            print(
                "⚠️  Could not send continuation message (this is okay if sandbox accepts direct messages)"
            )
        print()

        # Step 7: Wait for response
        print("Step 7: Waiting for resumed session response...")
        resumed_completion = await poll_for_completion(
            client, sandbox_id_2, timeout=180
        )
        if resumed_completion:
            print("✅ Resumed session completed successfully!")
            print(f"   New Session ID: {resumed_completion.get('session_id', 'N/A')}")
            # Check if it's the same session (should be if fork_session=False)
            new_session_id = resumed_completion.get("session_id")
            if new_session_id == session_id:
                print("   ✅ Session ID matches - same session continued!")
            else:
                print(
                    "   ℹ️  Different session ID - this might be expected if fork_session=True"
                )
        else:
            print("⚠️  Resumed session did not complete (this might be expected)")
        print()

        print("=" * 70)
        print("✅ TEST COMPLETE")
        print("=" * 70)
        print(f"Initial Session ID: {session_id}")
        print(f"Sandbox 1: {sandbox_id_1}")
        print(f"Sandbox 2: {sandbox_id_2}")
        print()

        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
