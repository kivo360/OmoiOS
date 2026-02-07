#!/usr/bin/env python3
"""Test and debug spec workflow API calls.

Use this script to verify MCP spec workflow operations and debug issues.
It directly calls the same API endpoints as the MCP tools.

Usage:
    cd backend
    set -a && source .env.local && set +a

    # List all specs for a project
    uv run python scripts/test_spec_workflow.py --list-specs --project-id proj-123

    # Get specific spec details
    uv run python scripts/test_spec_workflow.py --get-spec spec-456

    # Get ticket details
    uv run python scripts/test_spec_workflow.py --get-ticket ticket-789

    # Health check
    uv run python scripts/test_spec_workflow.py --health
"""

import argparse
import json
import os
import sys
from typing import Optional

import httpx

# Configuration
API_BASE = os.environ.get("OMOIOS_API_URL", "http://localhost:18000")
API_TIMEOUT = 30.0


def print_json(data: dict, indent: int = 2) -> None:
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent, default=str))


def health_check() -> bool:
    """Check if API is reachable."""
    print(f"Checking API health at {API_BASE}...")
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(f"{API_BASE}/health")
            if response.status_code == 200:
                print("✅ API is healthy")
                print_json(response.json())
                return True
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
    except httpx.ConnectError:
        print(f"❌ Cannot connect to API at {API_BASE}")
        print("   Make sure the backend server is running:")
        print("   uv run uvicorn omoi_os.api.main:app --host 0.0.0.0 --port 18000")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def list_specs(project_id: str) -> Optional[list]:
    """List all specs for a project."""
    print(f"Listing specs for project: {project_id}")
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(
                f"{API_BASE}/api/v1/specs",
                params={"project_id": project_id},
            )
            response.raise_for_status()
            specs = response.json()
            print(f"✅ Found {len(specs)} spec(s)")
            print_json(specs)
            return specs
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_spec(spec_id: str) -> Optional[dict]:
    """Get detailed spec information."""
    print(f"Getting spec: {spec_id}")
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(f"{API_BASE}/api/v1/specs/{spec_id}")
            response.raise_for_status()
            spec = response.json()
            print("✅ Spec found")
            print_json(spec)
            return spec
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_ticket(ticket_id: str) -> Optional[dict]:
    """Get detailed ticket information."""
    print(f"Getting ticket: {ticket_id}")
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(f"{API_BASE}/api/v1/tickets/{ticket_id}")
            response.raise_for_status()
            ticket = response.json()
            print("✅ Ticket found")
            print_json(ticket)
            return ticket
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def list_requirements(spec_id: str) -> Optional[list]:
    """List requirements for a spec."""
    print(f"Listing requirements for spec: {spec_id}")
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(f"{API_BASE}/api/v1/specs/{spec_id}/requirements")
            response.raise_for_status()
            reqs = response.json()
            print(f"✅ Found {len(reqs)} requirement(s)")
            print_json(reqs)
            return reqs
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def list_tasks(spec_id: str) -> Optional[list]:
    """List tasks for a spec."""
    print(f"Listing tasks for spec: {spec_id}")
    try:
        with httpx.Client(timeout=API_TIMEOUT) as client:
            response = client.get(f"{API_BASE}/api/v1/specs/{spec_id}/tasks")
            response.raise_for_status()
            tasks = response.json()
            print(f"✅ Found {len(tasks)} task(s)")
            print_json(tasks)
            return tasks
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP {e.response.status_code}: {e.response.text}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    global API_BASE
    parser = argparse.ArgumentParser(
        description="Test and debug spec workflow API calls"
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Check API health",
    )
    parser.add_argument(
        "--list-specs",
        action="store_true",
        help="List all specs for a project",
    )
    parser.add_argument(
        "--get-spec",
        type=str,
        metavar="SPEC_ID",
        help="Get spec details by ID",
    )
    parser.add_argument(
        "--get-ticket",
        type=str,
        metavar="TICKET_ID",
        help="Get ticket details by ID",
    )
    parser.add_argument(
        "--list-requirements",
        type=str,
        metavar="SPEC_ID",
        help="List requirements for a spec",
    )
    parser.add_argument(
        "--list-tasks",
        type=str,
        metavar="SPEC_ID",
        help="List tasks for a spec",
    )
    parser.add_argument(
        "--project-id",
        type=str,
        help="Project ID (required for --list-specs)",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        help=f"Override API URL (default: {API_BASE})",
    )

    args = parser.parse_args()

    # Override API URL if specified
    if args.api_url:
        API_BASE = args.api_url
        print(f"Using API URL: {API_BASE}")

    # Execute command
    if args.health:
        success = health_check()
        sys.exit(0 if success else 1)

    if args.list_specs:
        if not args.project_id:
            print("Error: --project-id is required for --list-specs")
            sys.exit(1)
        result = list_specs(args.project_id)
        sys.exit(0 if result is not None else 1)

    if args.get_spec:
        result = get_spec(args.get_spec)
        sys.exit(0 if result is not None else 1)

    if args.get_ticket:
        result = get_ticket(args.get_ticket)
        sys.exit(0 if result is not None else 1)

    if args.list_requirements:
        result = list_requirements(args.list_requirements)
        sys.exit(0 if result is not None else 1)

    if args.list_tasks:
        result = list_tasks(args.list_tasks)
        sys.exit(0 if result is not None else 1)

    # No command specified, show help
    parser.print_help()
    print("\nExamples:")
    print("  uv run python scripts/test_spec_workflow.py --health")
    print(
        "  uv run python scripts/test_spec_workflow.py --list-specs --project-id proj-123"
    )
    print("  uv run python scripts/test_spec_workflow.py --get-spec spec-456")
    print("  uv run python scripts/test_spec_workflow.py --list-requirements spec-456")


if __name__ == "__main__":
    main()
