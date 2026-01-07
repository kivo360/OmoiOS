"""Task Validator Service for verifying completed work.

This service spawns validator agents to review work before marking tasks as complete.
The validation workflow:

1. Implementer agent completes work and reports agent.completed
2. Task is marked as "pending_validation" (not "completed")
3. TaskValidatorService spawns a validator sandbox
4. Validator reviews code, runs tests, checks PR requirements
5. If validation passes -> task marked "completed"
6. If validation fails -> task marked "needs_revision" with feedback

The validator agent checks:
- Tests pass (runs pytest/npm test/etc.)
- Code builds successfully
- Changes are committed and pushed
- PR is created (if required)
- Code review checklist passes (security, quality, maintainability)
"""

import asyncio
import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

from omoi_os.logging import get_logger
from omoi_os.models.task import Task
from omoi_os.models.validation_review import ValidationReview
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


# Validation requirements that must be met
VALIDATION_REQUIREMENTS = {
    "tests_pass": {
        "description": "All tests must pass",
        "commands": ["pytest", "npm test", "go test ./...", "cargo test"],
        "required": True,
    },
    "build_passes": {
        "description": "Code must build successfully",
        "commands": ["npm run build", "cargo build", "go build ./..."],
        "required": True,
    },
    "changes_committed": {
        "description": "All changes must be committed",
        "check": "git status --porcelain returns empty",
        "required": True,
    },
    "changes_pushed": {
        "description": "Changes must be pushed to remote",
        "check": "git status shows ahead of remote by 0",
        "required": True,
    },
    "pr_created": {
        "description": "Pull request must be created",
        "check": "gh pr view returns PR info",
        "required": True,  # Based on user preference
    },
}


class TaskValidatorService:
    """Service for validating completed task work.

    This service is responsible for:
    1. Spawning validator agents to review completed work
    2. Tracking validation iterations and feedback
    3. Determining when tasks can be marked as truly complete
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
    ):
        self.db = db
        self.event_bus = event_bus
        self._validation_enabled = os.getenv("TASK_VALIDATION_ENABLED", "true").lower() in ("true", "1", "yes")
        self._max_validation_iterations = int(os.getenv("MAX_VALIDATION_ITERATIONS", "3"))

    async def request_validation(
        self,
        task_id: str,
        sandbox_id: str,
        implementation_result: dict,
    ) -> str:
        """Request validation for a completed task.

        This is called when an implementer agent reports completion.
        Instead of marking the task as completed, we:
        1. Update task status to "pending_validation"
        2. Store the implementation result
        3. Spawn a validator agent

        Args:
            task_id: ID of the task to validate
            sandbox_id: Sandbox where implementation was done
            implementation_result: Result data from the implementer

        Returns:
            Validation request ID
        """
        if not self._validation_enabled:
            logger.info(f"Validation disabled, auto-approving task {task_id}")
            return await self._auto_approve(task_id, implementation_result)

        validation_id = str(uuid4())

        async with self.db.get_async_session() as session:
            from sqlalchemy import select

            # Get the task
            result = await session.execute(
                select(Task).filter(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task {task_id} not found for validation")
                return ""

            # Count existing validation iterations
            review_count = await session.execute(
                select(ValidationReview).filter(ValidationReview.task_id == task_id)
            )
            iteration = len(list(review_count.scalars().all())) + 1

            if iteration > self._max_validation_iterations:
                logger.warning(
                    f"Task {task_id} exceeded max validation iterations ({self._max_validation_iterations}), "
                    "marking as failed"
                )
                task.status = "failed"
                task.error_message = f"Failed validation after {iteration - 1} iterations"
                await session.commit()
                return ""

            # Update task status
            task.status = "pending_validation"
            task.result = {
                **(task.result or {}),
                "implementation_result": implementation_result,
                "validation_requested_at": utc_now().isoformat(),
                "validation_iteration": iteration,
            }
            await session.commit()

            logger.info(
                f"Task {task_id} marked as pending_validation (iteration {iteration})"
            )

        # NOTE: We do NOT spawn the validator here anymore.
        # The orchestrator worker polls for pending_validation tasks and spawns
        # validation sandboxes via get_next_validation_task(). This ensures:
        # 1. No duplicate sandbox spawns (orchestrator uses atomic claims)
        # 2. Consistent validation flow through the orchestrator
        # 3. Proper concurrency limits are respected
        #
        # The _spawn_validator() method is kept for manual/testing use but is not
        # called in the normal flow.

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="TASK_VALIDATION_REQUESTED",
                    entity_type="task",
                    entity_id=task_id,
                    payload={
                        "validation_id": validation_id,
                        "iteration": iteration,
                        "sandbox_id": sandbox_id,
                    },
                )
            )

        return validation_id

    async def handle_validation_result(
        self,
        task_id: str,
        validator_agent_id: str,
        passed: bool,
        feedback: str,
        evidence: Optional[dict] = None,
        recommendations: Optional[list] = None,
    ) -> None:
        """Handle the result of a validation review.

        Args:
            task_id: Task that was validated
            validator_agent_id: Agent that performed validation
            passed: Whether validation passed
            feedback: Human-readable feedback
            evidence: Evidence of checks performed (test output, etc.)
            recommendations: List of recommendations if validation failed
        """
        async with self.db.get_async_session() as session:
            from sqlalchemy import select

            # Get task
            result = await session.execute(
                select(Task).filter(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task {task_id} not found for validation result")
                return

            # Count existing reviews
            review_result = await session.execute(
                select(ValidationReview).filter(ValidationReview.task_id == task_id)
            )
            iteration = len(list(review_result.scalars().all())) + 1

            # Create validation review record
            review = ValidationReview(
                task_id=task_id,
                validator_agent_id=validator_agent_id,
                iteration_number=iteration,
                validation_passed=passed,
                feedback=feedback,
                evidence=evidence or {},
                recommendations=recommendations or [],
            )
            session.add(review)

            if passed:
                # Validation passed - mark task as completed
                task.status = "completed"
                task.result = {
                    **(task.result or {}),
                    "validation_passed": True,
                    "validation_iteration": iteration,
                    "validated_at": utc_now().isoformat(),
                }
                logger.info(f"Task {task_id} validation PASSED on iteration {iteration}")

                if self.event_bus:
                    # Publish validation passed event
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="TASK_VALIDATION_PASSED",
                            entity_type="task",
                            entity_id=task_id,
                            payload={
                                "iteration": iteration,
                                "feedback": feedback,
                            },
                        )
                    )
                    # Also publish TASK_COMPLETED for sidebar/UI updates
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="TASK_COMPLETED",
                            entity_type="task",
                            entity_id=task_id,
                            payload={
                                "status": "completed",
                                "validation_passed": True,
                                "validation_iteration": iteration,
                            },
                        )
                    )
            else:
                # Validation failed - mark for revision
                task.status = "needs_revision"
                task.result = {
                    **(task.result or {}),
                    "validation_passed": False,
                    "validation_iteration": iteration,
                    "revision_feedback": feedback,
                    "revision_recommendations": recommendations or [],
                }
                logger.info(
                    f"Task {task_id} validation FAILED on iteration {iteration}, "
                    f"needs revision. Feedback: {feedback[:100]}..."
                )

                if self.event_bus:
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="TASK_VALIDATION_FAILED",
                            entity_type="task",
                            entity_id=task_id,
                            payload={
                                "iteration": iteration,
                                "feedback": feedback,
                                "recommendations": recommendations,
                            },
                        )
                    )
                    # Also publish status change event for sidebar/UI updates
                    self.event_bus.publish(
                        SystemEvent(
                            event_type="TASK_STATUS_CHANGED",
                            entity_type="task",
                            entity_id=task_id,
                            payload={
                                "status": "needs_revision",
                                "validation_passed": False,
                                "validation_iteration": iteration,
                            },
                        )
                    )

            await session.commit()

    async def _spawn_validator(
        self,
        task_id: str,
        original_sandbox_id: str,
        iteration: int,
    ) -> Optional[dict]:
        """Spawn a validator agent to review the task.

        The validator runs in the same sandbox as the implementation
        to have access to the code and git state.

        Args:
            task_id: Task to validate
            original_sandbox_id: Sandbox where implementation was done
            iteration: Validation iteration number

        Returns:
            Dict with sandbox_id and agent_id, or None if spawn failed
        """
        try:
            from omoi_os.services.daytona_spawner import get_daytona_spawner
            from omoi_os.models.ticket import Ticket
            from omoi_os.models.user import User

            spawner = get_daytona_spawner(db=self.db, event_bus=self.event_bus)

            # Get repo/branch info from the task's ticket
            extra_env = {
                "VALIDATION_MODE": "true",
                "ORIGINAL_TASK_ID": task_id,
                "VALIDATION_ITERATION": str(iteration),
                "ORIGINAL_SANDBOX_ID": original_sandbox_id,
            }

            with self.db.get_session() as session:
                # Get task with its ticket and project
                task = session.query(Task).filter(Task.id == task_id).first()
                if task and task.ticket_id:
                    ticket = session.query(Ticket).filter(Ticket.id == task.ticket_id).first()
                    if ticket and ticket.project:
                        project = ticket.project
                        # Set repo info
                        if project.github_owner and project.github_repo:
                            extra_env["GITHUB_REPO"] = f"{project.github_owner}/{project.github_repo}"
                            extra_env["GITHUB_REPO_OWNER"] = project.github_owner
                            extra_env["GITHUB_REPO_NAME"] = project.github_repo

                        # Get branch name from task result (set by implementer)
                        if task.result and task.result.get("branch_name"):
                            extra_env["BRANCH_NAME"] = task.result["branch_name"]
                        elif task.result and task.result.get("implementation_result"):
                            impl_result = task.result["implementation_result"]
                            if impl_result.get("branch_name"):
                                extra_env["BRANCH_NAME"] = impl_result["branch_name"]

                        # Get GitHub token from project owner
                        if project.created_by:
                            extra_env["USER_ID"] = str(project.created_by)
                            user = session.query(User).filter(User.id == project.created_by).first()
                            if user and user.attributes:
                                github_token = user.attributes.get("github_access_token")
                                if github_token:
                                    extra_env["GITHUB_TOKEN"] = github_token

            # Create validator agent record
            from omoi_os.models.agent import Agent

            validator_agent_id = str(uuid4())

            with self.db.get_session() as session:
                validator_agent = Agent(
                    id=validator_agent_id,
                    agent_type="validator",
                    phase_id="PHASE_VALIDATION",
                    capabilities=["validate", "test", "review"],
                    status="RUNNING",
                    tags=["validator", "daytona"],
                    health_status="healthy",
                )
                session.add(validator_agent)
                session.commit()

            # Build validator prompt
            validator_prompt = self._build_validator_prompt(task_id, iteration)
            extra_env["INITIAL_PROMPT"] = validator_prompt

            # Spawn validator sandbox with repo/branch info
            # The sandbox will clone the repo and checkout the branch
            # Use "validation" mode to load code-review and test-writer skills
            validator_sandbox_id = await spawner.spawn_for_task(
                task_id=f"{task_id}-validator-{iteration}",
                agent_id=validator_agent_id,
                phase_id="PHASE_VALIDATION",
                agent_type="validator",
                extra_env=extra_env,
                runtime="claude",
                execution_mode="validation",
            )

            logger.info(
                f"Spawned validator sandbox {validator_sandbox_id} for task {task_id} "
                f"(iteration {iteration})"
            )

            return {
                "sandbox_id": validator_sandbox_id,
                "agent_id": validator_agent_id,
            }

        except Exception as e:
            logger.error(f"Failed to spawn validator for task {task_id}: {e}")
            return None

    def _build_validator_prompt(self, task_id: str, iteration: int) -> str:
        """Build the prompt for the validator agent."""
        return f"""You are a code validator agent. Your job is to verify that the implementation work for task {task_id} is complete and meets quality standards.

## Validation Iteration: {iteration}

## Your Checklist

1. **Tests Pass**: Run the test suite and verify all tests pass
   - Try: `pytest`, `npm test`, `go test ./...`, `cargo test`
   - All tests MUST pass

2. **Build Passes**: Verify the code builds successfully
   - Try: `npm run build`, `cargo build`, `go build ./...`
   - No build errors allowed

3. **Changes Committed**: All changes must be committed to git
   - Run: `git status`
   - Working directory should be clean (no uncommitted changes)

4. **Changes Pushed**: All commits must be pushed to remote
   - Run: `git status`
   - Should not show "Your branch is ahead of..."

5. **PR Created**: A pull request must exist for this work
   - Run: `gh pr view`
   - Should show PR details with proper title and description

6. **Code Quality**: Review the code for:
   - Security vulnerabilities
   - Obvious bugs or logic errors
   - Missing error handling
   - Code style consistency

## Your Actions

1. Run each check in the checklist above
2. Collect evidence (command outputs, test results)
3. If ALL checks pass, report validation success
4. If ANY check fails, report validation failure with:
   - Which checks failed
   - What needs to be fixed
   - Specific recommendations

## Reporting Results

After completing your validation, you MUST report the result using the validation API.

If validation PASSES:
- Mark the task as validated
- Include a summary of what was verified

If validation FAILS:
- Provide specific feedback on what failed
- Give actionable recommendations for fixes
- The implementation agent will receive this feedback and retry

Begin your validation now. Start by checking the git status and running tests."""

    async def _auto_approve(self, task_id: str, result: dict) -> str:
        """Auto-approve a task when validation is disabled."""
        async with self.db.get_async_session() as session:
            from sqlalchemy import select

            result_query = await session.execute(
                select(Task).filter(Task.id == task_id)
            )
            task = result_query.scalar_one_or_none()

            if task:
                task.status = "completed"
                task.result = {
                    **(task.result or {}),
                    **result,
                    "auto_approved": True,
                    "completed_at": utc_now().isoformat(),
                }
                await session.commit()
                logger.info(f"Task {task_id} auto-approved (validation disabled)")

        return "auto-approved"


def get_task_validator(
    db: Optional[DatabaseService] = None,
    event_bus: Optional[EventBusService] = None,
) -> TaskValidatorService:
    """Get or create TaskValidatorService instance."""
    if db is None:
        from omoi_os.api.dependencies import get_db_service
        db = get_db_service()

    return TaskValidatorService(db=db, event_bus=event_bus)
