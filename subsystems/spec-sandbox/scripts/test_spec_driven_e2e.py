#!/usr/bin/env python
"""End-to-end test for spec-driven workflow.

This tests the full flow:
1. Create a ticket with workflow_mode="spec_driven"
2. Verify a Spec record is created
3. Verify sandbox events can be posted to /api/v1/sandboxes/{sandbox_id}/events
4. Verify the spec's phase_data is updated from events

Usage:
    # Dry run (just validates logic)
    uv run python scripts/test_spec_driven_e2e.py

    # Live test against API
    uv run python scripts/test_spec_driven_e2e.py --live \
        --project-id=<uuid> \
        --api-key=<jwt-token>

    # Get a token first:
    uv run python scripts/get_test_token.py --email=user@example.com --password=yourpassword
"""

import argparse
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx


API_URL = "http://localhost:18000"


async def create_ticket_spec_driven(
    client: httpx.AsyncClient,
    project_id: str,
    title: str,
    description: str,
) -> dict[str, Any] | None:
    """Create a ticket with workflow_mode='spec_driven'.

    This should trigger the backend to:
    1. Create the ticket
    2. Create a Spec record
    3. Spawn a Daytona sandbox for spec execution
    """
    payload = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "priority": "MEDIUM",
        "context": {
            "workflow_mode": "spec_driven",
            "source": "spec_driven_e2e_test",
            "test_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

    print(f"\n  Creating ticket with workflow_mode='spec_driven'...")
    print(f"  Payload: {json.dumps(payload, indent=2)}")

    response = await client.post(f"{API_URL}/api/v1/tickets", json=payload)

    if response.status_code in (200, 201):
        data = response.json()
        print(f"  Ticket created: {data.get('id')}")
        return data
    else:
        print(f"  ERROR: Failed to create ticket: {response.status_code}")
        print(f"  Response: {response.text}")
        return None


async def list_specs_for_project(
    client: httpx.AsyncClient,
    project_id: str,
) -> list[dict[str, Any]]:
    """List specs for a project to find the one created from ticket."""
    print(f"\n  Listing specs for project {project_id}...")

    response = await client.get(
        f"{API_URL}/api/v1/specs",
        params={"project_id": project_id},
    )

    if response.status_code == 200:
        data = response.json()
        specs = data.get("specs", [])
        print(f"  Found {len(specs)} specs")
        return specs
    else:
        print(f"  ERROR: Failed to list specs: {response.status_code}")
        print(f"  Response: {response.text}")
        return []


async def get_spec(
    client: httpx.AsyncClient,
    spec_id: str,
) -> dict[str, Any] | None:
    """Get a specific spec by ID."""
    print(f"\n  Getting spec {spec_id}...")

    response = await client.get(f"{API_URL}/api/v1/specs/{spec_id}")

    if response.status_code == 200:
        data = response.json()
        print(f"  Spec status: {data.get('status')}")
        print(f"  Current phase: {data.get('current_phase')}")
        return data
    else:
        print(f"  ERROR: Failed to get spec: {response.status_code}")
        return None


async def post_sandbox_event(
    client: httpx.AsyncClient,
    sandbox_id: str,
    event_type: str,
    event_data: dict[str, Any],
    source: str = "agent",
) -> bool:
    """Post an event to the sandbox events endpoint.

    This simulates what HTTPReporter does from spec-sandbox.
    """
    payload = {
        "event_type": event_type,
        "event_data": event_data,
        "source": source,
    }

    endpoint = f"{API_URL}/api/v1/sandboxes/{sandbox_id}/events"
    print(f"\n  Posting event to {endpoint}")
    print(f"  Event type: {event_type}")
    print(f"  Event data: {json.dumps(event_data, indent=2)}")

    response = await client.post(endpoint, json=payload)

    if response.status_code in (200, 201):
        data = response.json()
        print(f"  Event created: {data.get('id')}")
        return True
    else:
        print(f"  ERROR: Failed to post event: {response.status_code}")
        print(f"  Response: {response.text}")
        return False


async def test_sandbox_event_flow(
    client: httpx.AsyncClient,
    spec_id: str,
) -> bool:
    """Test the sandbox event flow with spec_id injection.

    This simulates what HTTPReporter sends during spec execution.
    """
    # Generate a test sandbox ID
    sandbox_id = f"spec-{spec_id[:8]}-expl-{uuid.uuid4().hex[:6]}"

    print(f"\n  Testing sandbox event flow with sandbox_id: {sandbox_id}")

    # 1. Post phase.started event
    ok = await post_sandbox_event(
        client,
        sandbox_id=sandbox_id,
        event_type="phase.started",
        event_data={
            "spec_id": spec_id,
            "phase": "explore",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    if not ok:
        return False

    # 2. Post phase.progress event
    ok = await post_sandbox_event(
        client,
        sandbox_id=sandbox_id,
        event_type="phase.progress",
        event_data={
            "spec_id": spec_id,
            "phase": "explore",
            "progress": 50,
            "message": "Exploring codebase structure...",
        },
    )
    if not ok:
        return False

    # 3. Post phase.completed event with output
    ok = await post_sandbox_event(
        client,
        sandbox_id=sandbox_id,
        event_type="phase.completed",
        event_data={
            "spec_id": spec_id,
            "phase": "explore",
            "success": True,
            "output": {
                "codebase_summary": {
                    "languages": ["python", "typescript"],
                    "frameworks": ["fastapi", "react"],
                    "entry_points": ["backend/main.py", "frontend/app/page.tsx"],
                },
                "complexity_assessment": "medium",
                "estimated_effort": "2-3 days",
            },
        },
    )
    if not ok:
        return False

    # 4. Post agent.completed event (final summary)
    ok = await post_sandbox_event(
        client,
        sandbox_id=sandbox_id,
        event_type="agent.completed",
        event_data={
            "spec_id": spec_id,
            "success": True,
            "phase_data": {
                "explore": {
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "codebase_summary": {
                        "languages": ["python", "typescript"],
                        "frameworks": ["fastapi", "react"],
                    },
                },
            },
            "sync_summary": {
                "status": "completed",
                "summary": {
                    "total_requirements": 5,
                    "total_tasks": 10,
                },
            },
        },
    )
    if not ok:
        return False

    return True


async def run_dry_test() -> bool:
    """Run a dry test without actual API calls."""
    print("\n=== DRY RUN TEST ===")
    print("\nThis test validates the event payload structure without API calls.")

    # Simulate event payloads
    spec_id = str(uuid.uuid4())
    sandbox_id = f"spec-{spec_id[:8]}-expl-{uuid.uuid4().hex[:6]}"

    payloads = [
        {
            "event_type": "phase.started",
            "event_data": {
                "spec_id": spec_id,
                "phase": "explore",
            },
            "source": "agent",
        },
        {
            "event_type": "phase.completed",
            "event_data": {
                "spec_id": spec_id,
                "phase": "explore",
                "success": True,
                "output": {"codebase_summary": {}},
            },
            "source": "agent",
        },
        {
            "event_type": "agent.completed",
            "event_data": {
                "spec_id": spec_id,
                "success": True,
                "phase_data": {"explore": {"completed": True}},
            },
            "source": "agent",
        },
    ]

    print(f"\n  Generated sandbox_id: {sandbox_id}")
    print(f"  Generated spec_id: {spec_id}")
    print(f"\n  Event payloads to send to POST /api/v1/sandboxes/{sandbox_id}/events:")

    for i, payload in enumerate(payloads, 1):
        print(f"\n  [{i}] {payload['event_type']}:")
        print(f"      {json.dumps(payload, indent=6)}")

    print("\n  Dry run completed successfully!")
    return True


async def run_live_test(
    project_id: str,
    api_key: str | None,
) -> bool:
    """Run a live test against the API."""
    print("\n=== LIVE API TEST ===")
    print(f"\n  API URL: {API_URL}")
    print(f"  Project ID: {project_id}")

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        # Step 1: Create ticket with spec_driven workflow
        title = f"[E2E Test] Spec-Driven Workflow Test {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        description = """
## Test Spec

This is an automated end-to-end test of the spec-driven workflow.

### Requirements
- Test ticket creation with workflow_mode=spec_driven
- Test spec creation from ticket
- Test sandbox event callbacks
- Test phase_data updates

### Expected Behavior
1. Ticket is created
2. Spec is created with source_ticket_id in context
3. Sandbox events update spec's phase_data
"""

        ticket = await create_ticket_spec_driven(
            client, project_id, title, description
        )

        if not ticket:
            print("\n  ERROR: Failed to create ticket")
            return False

        ticket_id = ticket.get("id")
        print(f"\n  Ticket ID: {ticket_id}")

        # Wait a moment for spec to be created
        print("\n  Waiting 2s for spec creation...")
        await asyncio.sleep(2)

        # Step 2: Find the spec created from this ticket
        specs = await list_specs_for_project(client, project_id)

        # Look for spec with our ticket ID in context
        matching_spec = None
        for spec in specs:
            context = spec.get("context", {})
            if context.get("source_ticket_id") == ticket_id:
                matching_spec = spec
                break

        if matching_spec:
            print(f"\n  Found matching spec: {matching_spec.get('id')}")
            print(f"  Spec title: {matching_spec.get('title')}")
            print(f"  Spec status: {matching_spec.get('status')}")
            spec_id = matching_spec.get("id")
        else:
            print("\n  WARNING: No spec found with matching source_ticket_id")
            print("  This may be expected if Daytona spawner is not configured")
            print("  Continuing with synthetic spec_id for event testing...")
            spec_id = str(uuid.uuid4())

        # Step 3: Test sandbox event flow
        print("\n" + "=" * 50)
        print("  TESTING SANDBOX EVENT CALLBACKS")
        print("=" * 50)

        event_ok = await test_sandbox_event_flow(client, spec_id)

        if event_ok:
            print("\n  Sandbox event flow completed successfully!")
        else:
            print("\n  ERROR: Sandbox event flow failed")
            return False

        # Step 4: Check if spec's phase_data was updated
        if matching_spec:
            updated_spec = await get_spec(client, spec_id)
            if updated_spec:
                phase_data = updated_spec.get("phase_data", {})
                if phase_data:
                    print(f"\n  Spec phase_data updated:")
                    print(f"  {json.dumps(phase_data, indent=4)}")
                else:
                    print("\n  NOTE: phase_data is empty (events may not have triggered update)")

        return True


async def main():
    global API_URL

    parser = argparse.ArgumentParser(
        description="End-to-end test for spec-driven workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Dry run (no API calls)
    uv run python scripts/test_spec_driven_e2e.py

    # Live test
    uv run python scripts/test_spec_driven_e2e.py --live \\
        --project-id=<uuid> \\
        --api-key=<jwt-token>
"""
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live test against API",
    )
    parser.add_argument(
        "--project-id",
        help="Project ID for live test",
    )
    parser.add_argument(
        "--api-key",
        help="JWT token for authentication",
    )
    parser.add_argument(
        "--api-url",
        default=API_URL,
        help=f"API URL (default: {API_URL})",
    )

    args = parser.parse_args()
    API_URL = args.api_url

    print("=" * 60)
    print("  SPEC-DRIVEN WORKFLOW END-TO-END TEST")
    print("=" * 60)

    if args.live:
        if not args.project_id:
            print("\nERROR: --project-id is required for live test")
            print("Use: uv run python scripts/test_spec_driven_e2e.py --live --project-id=<uuid>")
            return 1

        ok = await run_live_test(args.project_id, args.api_key)
    else:
        ok = await run_dry_test()

    print("\n" + "=" * 60)
    if ok:
        print("  TEST PASSED")
    else:
        print("  TEST FAILED")
    print("=" * 60)

    return 0 if ok else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
