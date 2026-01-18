#!/usr/bin/env python
"""DEVELOPMENT ONLY: Direct database sync test.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!! WARNING: This script connects DIRECTLY to the database, bypassing the API. !!
!! This is for development/debugging ONLY - NEVER use in production!          !!
!!                                                                            !!
!! For production sync, use the HTTP API via:                                 !!
!!   - MarkdownSyncService (spec_sandbox.sync)                                !!
!!   - CLI: spec-sandbox sync-markdown                                         !!
!!   - Test script: scripts/test_sync_via_http.py                             !!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

This script directly creates tickets/tasks in the database to verify
that the database schema and parsing work correctly during development.
"""

import asyncio
import json
import sys
import tempfile
from datetime import date
from pathlib import Path
from uuid import uuid4

# Add the backend to the path so we can import models
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "backend"))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

# Database URL from config/local.yaml
DATABASE_URL = "postgresql+psycopg://postgres:REDACTED_DB_PASSWORD@REDACTED_DB_HOST:5432/REDACTED_DB"


def create_test_markdown_files(base_dir: Path) -> None:
    """Create test markdown files with correct frontmatter schema."""
    tickets_dir = base_dir / "tickets"
    tasks_dir = base_dir / "tasks"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    tasks_dir.mkdir(parents=True, exist_ok=True)

    # Create ticket markdown
    ticket_md = f"""---
id: TKT-001
title: "[Spec-Sandbox Test] Authentication System"
created: {date.today().isoformat()}
status: backlog
priority: HIGH
estimate: M
requirements:
  - REQ-AUTH-001
---

## Description

This is a test ticket created by the spec-sandbox sync integration test.

### Requirements

1. Test the markdown sync pipeline
2. Verify frontmatter parsing works
3. Confirm database integration

### Notes

- Created by: spec-sandbox/scripts/test_sync_to_db.py
- Purpose: Verify end-to-end sync workflow
"""
    (tickets_dir / "TKT-001.md").write_text(ticket_md)
    print(f"✓ Created ticket file: {tickets_dir / 'TKT-001.md'}")

    return ticket_md


def list_projects(session: Session) -> list:
    """List all projects in the database."""
    result = session.execute(text("SELECT id, name, description FROM projects LIMIT 20"))
    return list(result.fetchall())


def list_tickets(session: Session, limit: int = 10) -> list:
    """List recent tickets."""
    result = session.execute(
        text("SELECT id, title, project_id, status, created_at FROM tickets ORDER BY created_at DESC LIMIT :limit"),
        {"limit": limit}
    )
    return list(result.fetchall())


def create_ticket_directly(
    session: Session,
    title: str,
    description: str,
    project_id: str,
    priority: str = "HIGH",
    context: dict = None,
) -> str:
    """Create a ticket directly in the database."""
    ticket_id = str(uuid4())

    session.execute(
        text("""
            INSERT INTO tickets (id, title, description, project_id, priority, phase_id, status, context, approval_status, created_at, updated_at)
            VALUES (:id, :title, :description, :project_id, :priority, :phase_id, :status, :context, :approval_status, NOW(), NOW())
        """),
        {
            "id": ticket_id,
            "title": title,
            "description": description,
            "project_id": project_id,
            "priority": priority,
            "phase_id": "PHASE_BACKLOG",
            "status": "backlog",
            "context": json.dumps(context) if context else None,
            "approval_status": "approved",
        }
    )
    session.commit()
    return ticket_id


def main():
    print("=" * 60)
    print("  SPEC-SANDBOX DATABASE SYNC TEST")
    print("=" * 60)
    print()

    # Connect to database
    print("Connecting to database...")
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        # List projects
        print("\n=== Available Projects ===")
        projects = list_projects(session)
        if not projects:
            print("No projects found. Please create a project first.")
            return 1

        for proj in projects:
            print(f"  [{proj[0][:8]}...] {proj[1]}")
            if proj[2]:
                print(f"       {proj[2][:50]}...")

        # Use the first project
        target_project_id = projects[0][0]
        print(f"\n✓ Using project: {projects[0][1]} ({target_project_id[:16]}...)")

        # List recent tickets
        print("\n=== Recent Tickets ===")
        tickets = list_tickets(session)
        if tickets:
            for ticket in tickets[:5]:
                print(f"  [{ticket[0][:8]}...] {ticket[1][:40]}... (status: {ticket[3]})")
        else:
            print("  No tickets found yet")

        # Create test markdown and sync
        print("\n=== Creating Test Ticket ===")
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            create_test_markdown_files(base_dir)

            # Now create the ticket directly from markdown
            from spec_sandbox.parsers.markdown import parse_ticket_markdown

            ticket_file = base_dir / "tickets" / "TKT-001.md"
            ticket_frontmatter, ticket_body = parse_ticket_markdown(ticket_file)

            print(f"  Parsed ticket: {ticket_frontmatter.title}")
            print(f"  Priority: {ticket_frontmatter.priority.value}")
            print(f"  Status: {ticket_frontmatter.status.value}")

            # Create in database
            ticket_id = create_ticket_directly(
                session,
                title=ticket_frontmatter.title,
                description=ticket_body,
                project_id=target_project_id,
                priority=ticket_frontmatter.priority.value,
                context={
                    "local_id": ticket_frontmatter.id,
                    "requirements": ticket_frontmatter.requirements,
                    "source": "spec_sandbox_test",
                }
            )

            print(f"\n✓ Created ticket in database: {ticket_id}")

        # Verify it was created
        print("\n=== Verifying Ticket ===")
        result = session.execute(
            text("SELECT id, title, status, created_at FROM tickets WHERE id = :id"),
            {"id": ticket_id}
        )
        created = result.fetchone()
        if created:
            print(f"  ID: {created[0]}")
            print(f"  Title: {created[1]}")
            print(f"  Status: {created[2]}")
            print(f"  Created: {created[3]}")
            print("\n✓ Ticket successfully created and verified!")
        else:
            print("ERROR: Ticket was not found after creation")
            return 1

    print("\n" + "=" * 60)
    print("  TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
