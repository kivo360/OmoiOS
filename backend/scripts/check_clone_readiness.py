#!/usr/bin/env python3
"""Check if sandbox can clone repos - diagnose GitHub token and project config.

Run with: cd backend && uv run python scripts/check_clone_readiness.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omoi_os.services.database import DatabaseService
from omoi_os.models.user import User
from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.models.task import Task


def main():
    print("=" * 60)
    print("Clone Readiness Check")
    print("=" * 60)

    # Load database URL from config
    from omoi_os.config import get_app_settings

    settings = get_app_settings()
    db = DatabaseService(settings.database.url)

    with db.get_session() as session:
        # Check 1: Users with GitHub tokens
        print("\n📋 USERS:")
        print("-" * 40)
        users = session.query(User).all()

        if not users:
            print("❌ No users found in database!")
        else:
            for user in users:
                attrs = user.attributes or {}
                github_token = attrs.get("github_access_token")
                github_username = attrs.get("github_username")

                token_preview = "None"
                if github_token:
                    # Show first/last 4 chars for verification
                    if len(github_token) > 10:
                        token_preview = f"{github_token[:4]}...{github_token[-4:]} ({len(github_token)} chars)"
                    else:
                        token_preview = f"[short: {len(github_token)} chars]"

                print(f"\n  User: {user.email}")
                print(f"    ID: {user.id}")
                print(f"    GitHub Username: {github_username or 'Not set'}")
                print(f"    GitHub Token: {token_preview}")
                print(
                    f"    All attributes keys: {list(attrs.keys()) if attrs else '[]'}"
                )

                if github_token:
                    print("    ✅ Has GitHub token")
                else:
                    print("    ❌ Missing GitHub token - OAuth connection needed!")

        # Check 2: Projects with GitHub config
        print("\n\n📁 PROJECTS:")
        print("-" * 40)
        projects = session.query(Project).all()

        if not projects:
            print("❌ No projects found in database!")
        else:
            for project in projects:
                print(f"\n  Project: {project.name}")
                print(f"    ID: {project.id}")
                print(f"    GitHub Owner: {project.github_owner or 'NOT SET'}")
                print(f"    GitHub Repo: {project.github_repo or 'NOT SET'}")
                print(f"    Created By: {project.created_by or 'NOT SET'}")

                if project.github_owner and project.github_repo:
                    print(
                        f"    ✅ GitHub config: {project.github_owner}/{project.github_repo}"
                    )
                else:
                    print("    ❌ Missing GitHub owner/repo!")

                # Check if owner has token
                if project.created_by:
                    owner = session.get(User, project.created_by)
                    if owner:
                        attrs = owner.attributes or {}
                        has_token = bool(attrs.get("github_access_token"))
                        if has_token:
                            print(
                                f"    ✅ Project owner ({owner.email}) has GitHub token"
                            )
                        else:
                            print(
                                f"    ❌ Project owner ({owner.email}) missing GitHub token!"
                            )

        # Check 3: Tickets and their projects
        print("\n\n🎫 RECENT TICKETS (last 5):")
        print("-" * 40)
        tickets = (
            session.query(Ticket).order_by(Ticket.created_at.desc()).limit(5).all()
        )

        if not tickets:
            print("❌ No tickets found!")
        else:
            for ticket in tickets:
                print(f"\n  Ticket: {ticket.title[:50]}...")
                print(f"    ID: {ticket.id}")
                print(f"    Status: {ticket.status}")
                print(f"    Project ID: {ticket.project_id or 'NOT LINKED'}")

                if ticket.project_id:
                    # Already loaded project above, just reference
                    if ticket.project:
                        gh = f"{ticket.project.github_owner}/{ticket.project.github_repo}"
                        if ticket.project.github_owner and ticket.project.github_repo:
                            print(f"    ✅ Linked to: {gh}")
                        else:
                            print("    ⚠️ Project exists but no GitHub config")
                    else:
                        print("    ⚠️ Project ID set but project not found")
                else:
                    print("    ❌ Not linked to any project - clone impossible!")

        # Check 4: Pending/Running tasks
        print("\n\n⏳ PENDING/RUNNING TASKS:")
        print("-" * 40)
        active_tasks = (
            session.query(Task)
            .filter(Task.status.in_(["pending", "assigned", "running", "claiming"]))
            .limit(10)
            .all()
        )

        if not active_tasks:
            print("No active tasks found.")
        else:
            clone_ready = 0
            clone_not_ready = 0

            for task in active_tasks:
                print(
                    f"\n  Task: {task.description[:50] if task.description else 'No description'}..."
                )
                print(f"    ID: {task.id}")
                print(f"    Status: {task.status}")
                print(f"    Ticket ID: {task.ticket_id}")

                ticket = session.get(Ticket, task.ticket_id) if task.ticket_id else None
                if not ticket:
                    print("    ❌ Ticket not found!")
                    clone_not_ready += 1
                    continue

                if not ticket.project_id:
                    print("    ❌ Ticket not linked to project!")
                    clone_not_ready += 1
                    continue

                project = ticket.project
                if not project:
                    print("    ❌ Project not found!")
                    clone_not_ready += 1
                    continue

                if not project.github_owner or not project.github_repo:
                    print("    ❌ Project missing GitHub config!")
                    clone_not_ready += 1
                    continue

                if not project.created_by:
                    print("    ❌ Project has no owner!")
                    clone_not_ready += 1
                    continue

                owner = session.get(User, project.created_by)
                if not owner:
                    print("    ❌ Project owner not found!")
                    clone_not_ready += 1
                    continue

                attrs = owner.attributes or {}
                if not attrs.get("github_access_token"):
                    print("    ❌ Owner missing GitHub token!")
                    clone_not_ready += 1
                    continue

                print(
                    f"    ✅ Clone ready: {project.github_owner}/{project.github_repo}"
                )
                clone_ready += 1

            print(
                f"\n  Summary: {clone_ready} tasks clone-ready, {clone_not_ready} NOT ready"
            )

        # Final summary
        print("\n\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        users_with_token = (
            sum(
                1
                for u in users
                if u.attributes and u.attributes.get("github_access_token")
            )
            if users
            else 0
        )

        projects_with_gh = (
            sum(1 for p in projects if p.github_owner and p.github_repo)
            if projects
            else 0
        )

        print(
            f"  Users with GitHub token: {users_with_token}/{len(users) if users else 0}"
        )
        print(
            f"  Projects with GitHub config: {projects_with_gh}/{len(projects) if projects else 0}"
        )

        if users_with_token == 0:
            print("\n  🔴 CRITICAL: No users have GitHub tokens!")
            print("     → User needs to connect GitHub via OAuth")
            print(
                "     → Token should be stored in user.attributes.github_access_token"
            )

        if projects_with_gh == 0:
            print("\n  🔴 CRITICAL: No projects have GitHub config!")
            print("     → Projects need github_owner and github_repo set")


if __name__ == "__main__":
    main()
