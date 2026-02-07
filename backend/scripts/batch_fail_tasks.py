#!/usr/bin/env python3
"""
Batch fail stale tasks via the API.

Usage:
    # Dry run (shows what would be failed)
    python scripts/batch_fail_tasks.py --dry-run

    # Actually fail the tasks
    python scripts/batch_fail_tasks.py

    # Fail tasks older than 2 days
    python scripts/batch_fail_tasks.py --hours 48

    # Fail specific task IDs
    python scripts/batch_fail_tasks.py --task-ids "id1,id2,id3"

Environment variables required:
    OMOIOS_API_TOKEN - Your API authentication token (JWT)
    OMOIOS_API_URL - API base URL (default: https://api.omoios.dev)
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

import httpx


def get_api_client(base_url: str, token: str) -> httpx.Client:
    """Create an authenticated HTTP client."""
    return httpx.Client(
        base_url=base_url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def get_stale_tasks(client: httpx.Client, hours: int = 24) -> list[dict]:
    """
    Fetch tasks that are pending/running/assigned and older than specified hours.
    """

    # Get all tasks and filter locally (API may not have complex filtering)
    def fetch_tasks(status: str) -> list[dict]:
        response = client.get("/api/v1/tasks", params={"status": status})
        if response.status_code == 200:
            data = response.json()
            # Handle both list and dict responses
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return data.get("tasks", [])
        return []

    running_tasks = fetch_tasks("running")
    pending_tasks = fetch_tasks("pending")
    assigned_tasks = fetch_tasks("assigned")

    all_tasks = running_tasks + pending_tasks + assigned_tasks

    # Filter by age
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stale_tasks = []

    for task in all_tasks:
        # Parse created_at or updated_at
        task_time_str = task.get("updated_at") or task.get("created_at")
        if task_time_str:
            try:
                # Handle various datetime formats
                if task_time_str.endswith("Z"):
                    task_time_str = task_time_str[:-1] + "+00:00"
                task_time = datetime.fromisoformat(task_time_str)
                if task_time.tzinfo is None:
                    task_time = task_time.replace(tzinfo=timezone.utc)
                if task_time < cutoff:
                    stale_tasks.append(task)
            except (ValueError, TypeError):
                # If we can't parse the date, include it to be safe
                stale_tasks.append(task)

    return stale_tasks


def fail_task(client: httpx.Client, task_id: str, reason: str) -> dict:
    """Mark a single task as failed using PATCH endpoint."""
    # Use PATCH to update task status (the /fail endpoint may not be deployed)
    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "failed", "error_message": reason},
    )
    return {
        "task_id": task_id,
        "status_code": response.status_code,
        "response": response.json() if response.status_code < 500 else response.text,
    }


def main():
    parser = argparse.ArgumentParser(description="Batch fail stale tasks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be failed without actually failing",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=24,
        help="Fail tasks older than this many hours (default: 24)",
    )
    parser.add_argument(
        "--task-ids",
        type=str,
        help="Comma-separated list of specific task IDs to fail",
    )
    parser.add_argument(
        "--reason",
        type=str,
        default="Stale task - batch cleanup",
        help="Reason for failing the tasks",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=os.environ.get("OMOIOS_API_URL", "https://api.omoios.dev"),
        help="API base URL",
    )

    args = parser.parse_args()

    # Get API token
    token = os.environ.get("OMOIOS_API_TOKEN")
    if not token:
        print("ERROR: OMOIOS_API_TOKEN environment variable is required")
        print("You can get this from your browser's localStorage or cookies")
        sys.exit(1)

    client = get_api_client(args.api_url, token)

    # Get tasks to fail
    if args.task_ids:
        # Specific task IDs provided
        task_ids = [tid.strip() for tid in args.task_ids.split(",")]
        tasks_to_fail = [{"id": tid} for tid in task_ids]
        print(f"Will fail {len(tasks_to_fail)} specified tasks")
    else:
        # Find stale tasks
        print(f"Finding tasks older than {args.hours} hours...")
        tasks_to_fail = get_stale_tasks(client, args.hours)
        print(f"Found {len(tasks_to_fail)} stale tasks")

    if not tasks_to_fail:
        print("No tasks to fail")
        return

    # Show tasks
    print("\nTasks to fail:")
    print("-" * 80)
    for task in tasks_to_fail:
        task_id = task.get("id", "unknown")
        status = task.get("status", "unknown")
        task_type = task.get("task_type", "unknown")
        title = (task.get("title") or task.get("description") or "No title")[:50]
        created = task.get("created_at", "unknown")
        print(
            f"  {task_id[:8]}... | {status:10} | {task_type:20} | {title} | {created}"
        )
    print("-" * 80)

    if args.dry_run:
        print("\nDRY RUN - No tasks were actually failed")
        print(f"Run without --dry-run to fail these {len(tasks_to_fail)} tasks")
        return

    # Confirm
    confirm = input(f"\nFail {len(tasks_to_fail)} tasks? [y/N]: ")
    if confirm.lower() != "y":
        print("Aborted")
        return

    # Fail tasks
    print("\nFailing tasks...")
    succeeded = 0
    failed = 0

    for task in tasks_to_fail:
        task_id = task.get("id")
        if not task_id:
            continue

        result = fail_task(client, task_id, args.reason)
        if result["status_code"] == 200:
            print(f"  ✓ {task_id[:8]}... failed successfully")
            succeeded += 1
        else:
            print(f"  ✗ {task_id[:8]}... error: {result['response']}")
            failed += 1

    print(f"\nDone: {succeeded} succeeded, {failed} failed")


if __name__ == "__main__":
    main()
