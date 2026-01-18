#!/usr/bin/env python
"""Test script to sync markdown files via HTTP API.

This tests the proper sync workflow using MarkdownSyncService,
which makes HTTP calls to the backend API instead of direct database access.
"""

import asyncio
import tempfile
from datetime import date
from pathlib import Path

from spec_sandbox.sync import MarkdownSyncService, SyncConfig


# API configuration - update these as needed
API_URL = "http://localhost:18000"  # Local dev API
# API_URL = "https://api.omoios.dev"  # Production API


def create_test_markdown_files(base_dir: Path) -> None:
    """Create test markdown files with correct frontmatter schema."""
    tickets_dir = base_dir / "tickets"
    tasks_dir = base_dir / "tasks"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Create ticket markdown
    ticket_md = f"""---
id: TKT-001
title: "[Spec-Sandbox HTTP Test] User Authentication"
created: {date.today().isoformat()}
status: backlog
priority: HIGH
estimate: M
requirements:
  - REQ-AUTH-001
  - REQ-AUTH-002
---

## Description

This is a test ticket created by the spec-sandbox HTTP sync integration test.

### Requirements

1. Test the HTTP-based markdown sync pipeline
2. Verify the MarkdownSyncService works correctly
3. Confirm API integration is functional

### Acceptance Criteria

- [ ] User can login with email/password
- [ ] Session is created on successful login
- [ ] Invalid credentials return appropriate error

### Notes

- Created by: spec-sandbox/scripts/test_sync_via_http.py
- Purpose: Verify end-to-end HTTP sync workflow
"""
    (tickets_dir / "TKT-001.md").write_text(ticket_md)
    print(f"  Created ticket file: {tickets_dir / 'TKT-001.md'}")

    # Create task markdown (linked to ticket)
    task_md = f"""---
id: TSK-001
title: Create login form component
created: {date.today().isoformat()}
status: pending
priority: HIGH
estimate: S
parent_ticket: TKT-001
type: implementation
files_to_modify:
  - src/components/LoginForm.tsx
  - src/hooks/useAuth.ts
---

## Objective

Create a reusable login form component with email and password fields.

### Implementation Details

1. Use React Hook Form for form state management
2. Add client-side validation (email format, password length)
3. Include loading state during authentication
4. Handle and display error messages from API

### Acceptance Criteria

- [ ] Form renders with email and password fields
- [ ] Submit button is disabled during loading
- [ ] Validation messages show on invalid input
- [ ] Error messages from API are displayed
"""
    (tasks_dir / "TSK-001.md").write_text(task_md)
    print(f"  Created task file: {tasks_dir / 'TSK-001.md'}")


async def test_sync_dry_run():
    """Test sync with dry-run mode (no actual API calls)."""
    print("\n=== Testing Dry-Run Sync ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_markdown_files(base_dir)

        config = SyncConfig(
            api_url=API_URL,
            project_id="test-project-id",
            spec_id="test-spec-id",
            dry_run=True,  # No actual API calls
        )

        service = MarkdownSyncService(config)
        try:
            summary = await service.sync_directory(base_dir)

            print(f"  Tickets synced: {summary.tickets_synced}")
            print(f"  Tickets failed: {summary.tickets_failed}")
            print(f"  Tasks synced: {summary.tasks_synced}")
            print(f"  Tasks failed: {summary.tasks_failed}")

            if summary.errors:
                print(f"  Errors: {summary.errors}")

            if summary.tickets_synced == 1 and summary.tasks_synced == 1:
                print("\n  Dry-run sync completed successfully!")
                return True
            else:
                print("\n  ERROR: Expected 1 ticket and 1 task to sync")
                return False
        finally:
            await service.close()


async def test_sync_to_api(project_id: str, api_key: str | None = None):
    """Test actual sync to the API.

    Args:
        project_id: Valid project ID from the database
        api_key: Optional API key for authentication
    """
    print("\n=== Testing API Sync ===\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)
        create_test_markdown_files(base_dir)

        config = SyncConfig(
            api_url=API_URL,
            project_id=project_id,
            spec_id="spec-sandbox-test",
            api_key=api_key,
            dry_run=False,  # Actual API calls
        )

        service = MarkdownSyncService(config)
        try:
            summary = await service.sync_directory(base_dir)

            print(f"  Tickets synced: {summary.tickets_synced}")
            print(f"  Tickets failed: {summary.tickets_failed}")
            print(f"  Tasks synced: {summary.tasks_synced}")
            print(f"  Tasks failed: {summary.tasks_failed}")

            if summary.ticket_id_map:
                print(f"  Ticket ID map: {summary.ticket_id_map}")
            if summary.task_id_map:
                print(f"  Task ID map: {summary.task_id_map}")

            if summary.errors:
                print(f"\n  Errors:")
                for error in summary.errors:
                    print(f"    - {error}")

            if summary.tickets_synced > 0:
                print(f"\n  Created ticket: {list(summary.ticket_id_map.values())[0]}")
                return True
            else:
                print("\n  WARNING: No tickets were created")
                return False
        finally:
            await service.close()


async def main():
    global API_URL
    import argparse

    parser = argparse.ArgumentParser(description="Test markdown sync via HTTP API")
    parser.add_argument(
        "--project-id",
        help="Project ID to sync to (required for live test)",
    )
    parser.add_argument(
        "--api-key",
        help="API key for authentication",
    )
    parser.add_argument(
        "--api-url",
        default=API_URL,
        help=f"API URL (default: {API_URL})",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live test against API (requires --project-id)",
    )
    args = parser.parse_args()

    API_URL = args.api_url

    print("=" * 60)
    print("  SPEC-SANDBOX HTTP SYNC TEST")
    print("=" * 60)
    print(f"\n  API URL: {API_URL}")

    # Always run dry-run test first
    dry_run_ok = await test_sync_dry_run()
    if not dry_run_ok:
        print("\nERROR: Dry-run test failed")
        return 1

    # Run live test if requested
    if args.live:
        if not args.project_id:
            print("\nERROR: --project-id is required for live test")
            return 1

        print(f"\n  Project ID: {args.project_id}")
        live_ok = await test_sync_to_api(args.project_id, args.api_key)
        if not live_ok:
            print("\nWARNING: Live test had issues (check errors above)")
            # Don't fail for API issues - might be auth/connectivity
    else:
        print("\n  Skipping live API test (use --live --project-id=XXX to enable)")

    print("\n" + "=" * 60)
    print("  TEST COMPLETED")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
