"""Spec Completion Service for automated PR creation after spec execution.

This service handles post-completion actions for specs:
1. Create a branch for the spec (if not exists)
2. Create a PR when all spec tickets are completed
3. Update spec with PR tracking info
"""

import logging
import re
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from omoi_os.logging import get_logger
from omoi_os.models.project import Project
from omoi_os.models.spec import Spec, SpecTask
from omoi_os.models.ticket import Ticket
from omoi_os.models.user import User
from omoi_os.services.branch_workflow import BranchWorkflowService
from omoi_os.services.credentials import CredentialsService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.github_api import GitHubAPIService

logger = get_logger(__name__)


def slugify(text: str, max_length: int = 50) -> str:
    """Convert text to URL-safe slug.

    Args:
        text: Text to slugify
        max_length: Maximum length of slug

    Returns:
        Lowercase slug with hyphens
    """
    # Convert to lowercase
    slug = text.lower()
    # Replace non-alphanumeric with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Truncate
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug


class SpecCompletionService:
    """Service for handling spec completion and PR creation."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        self.db = db
        self.event_bus = event_bus
        self.github_service = GitHubAPIService(db)
        self.branch_workflow = BranchWorkflowService(self.github_service)
        self.cred_service = CredentialsService(db)

    def _generate_branch_name(self, spec: Spec) -> str:
        """Generate a branch name for a spec.

        Format: spec/{spec_id_prefix}-{slug}
        Example: spec/abc12345-add-user-authentication

        Args:
            spec: Spec to generate branch name for

        Returns:
            Branch name string
        """
        spec_prefix = spec.id[:8] if spec.id.startswith("spec-") else spec.id[5:13]
        title_slug = slugify(spec.title, max_length=50)
        return f"spec/{spec_prefix}-{title_slug}"

    def _generate_pr_body(self, spec: Spec, tasks: list[SpecTask]) -> str:
        """Generate PR body from spec content.

        Args:
            spec: Spec to generate body from
            tasks: Spec tasks for the PR

        Returns:
            Markdown formatted PR body
        """
        body_parts = [
            f"## 📋 {spec.title}",
            "",
        ]

        if spec.description:
            body_parts.extend([spec.description, "", "---", ""])

        # Add tasks completed section
        if tasks:
            body_parts.append("### ✅ Tasks Completed")
            body_parts.append("")
            for task in tasks:
                status_icon = "✅" if task.status == "completed" else "⏳"
                body_parts.append(f"- {status_icon} {task.title}")
            body_parts.append("")

        # Add spec link
        body_parts.extend([
            "---",
            f"*Automated PR for spec `{spec.id}`*",
        ])

        return "\n".join(body_parts)

    async def create_branch_for_spec(
        self,
        spec_id: str,
        user_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Create a git branch for a spec.

        This should be called when spec execution starts.

        Args:
            spec_id: Spec ID
            user_id: Optional user ID (fetched from spec if not provided)

        Returns:
            Dict with success status and branch_name
        """
        async with self.db.get_async_session() as session:
            # Load spec with project
            result = await session.execute(
                select(Spec)
                .filter(Spec.id == spec_id)
                .options(selectinload(Spec.project))
            )
            spec = result.scalar_one_or_none()

            if not spec:
                return {"success": False, "error": "Spec not found"}

            # Use provided user_id or spec's user_id
            effective_user_id = user_id or spec.user_id
            if not effective_user_id:
                return {"success": False, "error": "No user associated with spec"}

            # Check if branch already exists
            if spec.branch_name:
                logger.info(f"Branch already exists for spec {spec_id}: {spec.branch_name}")
                return {"success": True, "branch_name": spec.branch_name}

            # Get project GitHub info
            project = spec.project
            if not project or not project.github_owner or not project.github_repo:
                return {
                    "success": False,
                    "error": "Project has no GitHub repository configured",
                }

            # Generate branch name
            branch_name = self._generate_branch_name(spec)

            # Get user's GitHub token
            github_creds = self.cred_service.get_github_credentials(
                user_id=effective_user_id
            )
            if not github_creds.access_token:
                return {
                    "success": False,
                    "error": "User has no GitHub credentials configured",
                }

            # Create branch via BranchWorkflowService
            try:
                result = await self.branch_workflow.start_work_on_ticket(
                    ticket_id=spec_id,  # Use spec_id as ticket_id
                    ticket_title=spec.title,
                    repo_owner=project.github_owner,
                    repo_name=project.github_repo,
                    user_id=str(effective_user_id),
                    ticket_type="spec",
                    branch_prefix="spec",  # Use spec/ prefix
                )

                if result.get("success"):
                    # Update spec with branch name
                    created_branch = result.get("branch_name", branch_name)
                    spec.branch_name = created_branch
                    await session.commit()

                    logger.info(f"Created branch {created_branch} for spec {spec_id}")

                    if self.event_bus:
                        self.event_bus.publish(
                            SystemEvent(
                                event_type="spec.branch_created",
                                entity_type="spec",
                                entity_id=spec_id,
                                payload={
                                    "branch_name": created_branch,
                                    "repo": f"{project.github_owner}/{project.github_repo}",
                                },
                            )
                        )

                    return {
                        "success": True,
                        "branch_name": created_branch,
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", "Failed to create branch"),
                    }

            except Exception as e:
                logger.error(f"Failed to create branch for spec {spec_id}: {e}")
                return {"success": False, "error": str(e)}

    async def create_pr_for_spec(
        self,
        spec_id: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Create a pull request for a completed spec.

        Args:
            spec_id: Spec ID
            force: If True, create PR even if tickets aren't completed

        Returns:
            Dict with success status, pr_number, pr_url
        """
        async with self.db.get_async_session() as session:
            # Load spec with project and tasks
            result = await session.execute(
                select(Spec)
                .filter(Spec.id == spec_id)
                .options(
                    selectinload(Spec.project),
                    selectinload(Spec.tasks),
                )
            )
            spec = result.scalar_one_or_none()

            if not spec:
                return {"success": False, "error": "Spec not found"}

            # Check if PR already exists
            if spec.pull_request_url:
                return {
                    "success": True,
                    "pr_number": spec.pull_request_number,
                    "pr_url": spec.pull_request_url,
                    "already_exists": True,
                }

            # Verify user
            if not spec.user_id:
                return {"success": False, "error": "No user associated with spec"}

            # Get project GitHub info
            project = spec.project
            if not project or not project.github_owner or not project.github_repo:
                return {
                    "success": False,
                    "error": "Project has no GitHub repository configured",
                }

            # Check branch exists
            if not spec.branch_name:
                return {
                    "success": False,
                    "error": "No branch exists for this spec - create branch first",
                }

            # Check all tasks are completed (unless force=True)
            if not force:
                incomplete_tasks = [t for t in spec.tasks if t.status != "completed"]
                if incomplete_tasks:
                    return {
                        "success": False,
                        "error": f"{len(incomplete_tasks)} tasks not yet completed",
                        "incomplete_tasks": [t.id for t in incomplete_tasks],
                    }

            # Generate PR body
            pr_body = self._generate_pr_body(spec, list(spec.tasks))
            pr_title = f"feat: {spec.title}"

            # Create PR via BranchWorkflowService
            try:
                result = await self.branch_workflow.finish_work_on_ticket(
                    ticket_id=spec_id,
                    ticket_title=spec.title,
                    branch_name=spec.branch_name,
                    repo_owner=project.github_owner,
                    repo_name=project.github_repo,
                    user_id=str(spec.user_id),
                    pr_body=pr_body,
                )

                if result.get("success"):
                    pr_number = result.get("pr_number")
                    pr_url = result.get("pr_url")

                    # Update spec with PR info
                    spec.pull_request_number = pr_number
                    spec.pull_request_url = pr_url
                    spec.status = "pr_created"
                    await session.commit()

                    logger.info(f"Created PR #{pr_number} for spec {spec_id}: {pr_url}")

                    if self.event_bus:
                        self.event_bus.publish(
                            SystemEvent(
                                event_type="spec.pr_created",
                                entity_type="spec",
                                entity_id=spec_id,
                                payload={
                                    "pr_number": pr_number,
                                    "pr_url": pr_url,
                                    "branch_name": spec.branch_name,
                                },
                            )
                        )

                    return {
                        "success": True,
                        "pr_number": pr_number,
                        "pr_url": pr_url,
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error", "Failed to create PR"),
                    }

            except Exception as e:
                logger.error(f"Failed to create PR for spec {spec_id}: {e}")
                return {"success": False, "error": str(e)}

    async def on_all_tickets_complete(self, spec_id: str) -> dict[str, Any]:
        """Handle completion of all tickets for a spec.

        This is the main entry point called when all spec tickets are done.
        It checks completion status and creates a PR.

        Args:
            spec_id: Spec ID

        Returns:
            Dict with success status and PR info
        """
        logger.info(f"Checking spec {spec_id} for completion...")

        async with self.db.get_async_session() as session:
            # Load spec with tasks
            result = await session.execute(
                select(Spec)
                .filter(Spec.id == spec_id)
                .options(selectinload(Spec.tasks))
            )
            spec = result.scalar_one_or_none()

            if not spec:
                return {"success": False, "error": "Spec not found"}

            # Check all tasks completed
            incomplete_tasks = [t for t in spec.tasks if t.status != "completed"]
            if incomplete_tasks:
                logger.info(
                    f"Spec {spec_id} has {len(incomplete_tasks)} incomplete tasks"
                )
                return {
                    "success": False,
                    "complete": False,
                    "incomplete_count": len(incomplete_tasks),
                }

        # All tasks complete - create branch if needed
        if not spec.branch_name:
            branch_result = await self.create_branch_for_spec(spec_id)
            if not branch_result.get("success"):
                logger.warning(f"Failed to create branch for spec {spec_id}")
                # Continue anyway - PR creation will fail if branch doesn't exist

        # Create PR
        pr_result = await self.create_pr_for_spec(spec_id)

        return pr_result


def get_spec_completion_service(
    db: DatabaseService,
    event_bus: Optional[EventBusService] = None,
) -> SpecCompletionService:
    """Get an instance of SpecCompletionService.

    Args:
        db: Database service
        event_bus: Optional event bus service

    Returns:
        SpecCompletionService instance
    """
    return SpecCompletionService(db=db, event_bus=event_bus)
