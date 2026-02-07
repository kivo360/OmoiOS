"""Validation orchestrator service for task validation workflow."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Dict, List, Optional
from uuid import uuid4

from omoi_os.logging import get_logger
from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.validation_review import ValidationReview
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)

if TYPE_CHECKING:
    from omoi_os.services.agent_registry import AgentRegistryService
    from omoi_os.services.diagnostic import DiagnosticService
    from omoi_os.services.memory import MemoryService


class ValidationState:
    """Validation state constants matching REQ-VAL-SM-001."""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    VALIDATION_IN_PROGRESS = "validation_in_progress"
    NEEDS_WORK = "needs_work"
    DONE = "done"
    FAILED = "failed"


class ValidationOrchestrator:
    """Orchestrator for validation state machine and validator agent coordination.

    Implements REQ-VAL-SM-001, REQ-VAL-LC-001, REQ-VAL-LC-002:
    - Enforces validation state machine transitions
    - Spawns validator agents when tasks enter under_review
    - Handles validation reviews and feedback delivery
    - Integrates with Memory and Diagnosis systems
    """

    def __init__(
        self,
        db: DatabaseService,
        agent_registry: "AgentRegistryService",
        memory: Optional["MemoryService"] = None,
        diagnostic: Optional["DiagnosticService"] = None,
        event_bus: Optional[EventBusService] = None,
    ):
        """Initialize validation orchestrator.

        Args:
            db: Database service
            agent_registry: Agent registry service for spawning validators
            memory: Optional memory service for recording validation outcomes
            diagnostic: Optional diagnostic service for auto-spawn on failures
            event_bus: Optional event bus for publishing validation events
        """
        self.db = db
        self.agent_registry = agent_registry
        self.memory = memory
        self.diagnostic = diagnostic
        self.event_bus = event_bus
        self._active_validators: Dict[str, str] = {}  # task_id -> validator_agent_id

    # -------------------------------------------------------------------------
    # State Machine Transitions
    # -------------------------------------------------------------------------

    def transition_to_under_review(
        self,
        task_id: str,
        commit_sha: Optional[str] = None,
    ) -> bool:
        """Transition task to under_review state (REQ-VAL-SM-002).

        Preconditions:
            - Worker agent has published completion signal
            - If Git-backed workspace, commit_sha must be provided

        Side effects:
            - Increment validation_iteration by 1
            - Set review_done = False
            - Spawn validator if validation_enabled = True

        Args:
            task_id: Task ID to transition
            commit_sha: Optional Git commit SHA for validation

        Returns:
            True if transition successful, False if task not found

        Raises:
            ValueError: If validation enabled but commit_sha missing for Git-backed task
        """
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return False

            # Guard: commit_sha required if validation enabled (REQ-VAL-SM-002)
            if task.validation_enabled and not commit_sha:
                raise ValueError(
                    f"commit_sha required for task {task_id} with validation_enabled=True"
                )

            # Update task state
            task.status = ValidationState.UNDER_REVIEW
            task.validation_iteration += 1
            task.review_done = False

            # Store commit_sha in metadata if provided
            if commit_sha:
                if not task.result:
                    task.result = {}
                task.result["validation_commit_sha"] = commit_sha

            session.commit()

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="task.status.changed",
                        entity_type="task",
                        entity_id=task_id,
                        payload={
                            "previous_status": "in_progress",
                            "new_status": ValidationState.UNDER_REVIEW,
                            "validation_iteration": task.validation_iteration,
                        },
                    )
                )

            # Spawn validator if validation enabled (REQ-VAL-LC-001)
            if task.validation_enabled:
                validator_id = self.spawn_validator(task_id, commit_sha)
                if validator_id:
                    self._active_validators[task_id] = validator_id

            return True

    def transition_to_validation_in_progress(
        self,
        task_id: str,
        validator_agent_id: str,
    ) -> bool:
        """Transition task to validation_in_progress state.

        Preconditions:
            - Validator agent successfully spawned

        Side effects:
            - Set task status to validation_in_progress
            - Emit validation_started event

        Args:
            task_id: Task ID
            validator_agent_id: ID of spawned validator agent

        Returns:
            True if transition successful, False if task not found
        """
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return False

            task.status = ValidationState.VALIDATION_IN_PROGRESS
            session.commit()

            # Emit validation_started event (REQ-VAL-Events)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="validation_started",
                        entity_type="task",
                        entity_id=task_id,
                        payload={
                            "task_id": task_id,
                            "iteration": task.validation_iteration,
                            "validator_agent_id": validator_agent_id,
                        },
                    )
                )

            return True

    def transition_to_done(
        self,
        task_id: str,
        review: ValidationReview,
    ) -> bool:
        """Transition task to done state after successful validation.

        Preconditions:
            - Received give_review with validation_passed == True

        Side effects:
            - Set task status to done
            - Set review_done = True
            - Persist ValidationReview
            - Emit validation_passed event
            - Write Memory entry (REQ-VAL-MEM-001)

        Args:
            task_id: Task ID
            review: ValidationReview with validation_passed=True

        Returns:
            True if transition successful, False if task not found
        """
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return False

            # Persist review
            session.add(review)

            # Update task state
            task.status = ValidationState.DONE
            task.review_done = True

            # Clear active validator
            self._active_validators.pop(task_id, None)

            session.commit()

            # Emit events (REQ-VAL-Events)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="validation_review_submitted",
                        entity_type="validation_review",
                        entity_id=review.id,
                        payload={
                            "task_id": task_id,
                            "iteration": review.iteration_number,
                            "passed": True,
                            "validator_agent_id": review.validator_agent_id,
                        },
                    )
                )
                self.event_bus.publish(
                    SystemEvent(
                        event_type="validation_passed",
                        entity_type="task",
                        entity_id=task_id,
                        payload={
                            "task_id": task_id,
                            "iteration": review.iteration_number,
                        },
                    )
                )

            # Write Memory entry (REQ-VAL-MEM-001)
            if self.memory and task.ticket_id:
                self._record_validation_memory(review, task.ticket_id)

            return True

    def transition_to_needs_work(
        self,
        task_id: str,
        review: ValidationReview,
    ) -> bool:
        """Transition task to needs_work state after failed validation.

        Preconditions:
            - Received give_review with validation_passed == False and non-empty feedback

        Side effects:
            - Set task status to needs_work
            - Set last_validation_feedback
            - Persist ValidationReview
            - Emit validation_failed event
            - Write Memory entry (REQ-VAL-MEM-001)
            - Check for repeated failures and spawn Diagnosis if needed (REQ-VAL-DIAG-001)

        Args:
            task_id: Task ID
            review: ValidationReview with validation_passed=False

        Returns:
            True if transition successful, False if task not found
        """
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return False

            # Persist review
            session.add(review)

            # Update task state
            task.status = ValidationState.NEEDS_WORK
            task.last_validation_feedback = review.feedback

            # Clear active validator
            self._active_validators.pop(task_id, None)

            session.commit()

            # Emit events (REQ-VAL-Events)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="validation_review_submitted",
                        entity_type="validation_review",
                        entity_id=review.id,
                        payload={
                            "task_id": task_id,
                            "iteration": review.iteration_number,
                            "passed": False,
                            "validator_agent_id": review.validator_agent_id,
                        },
                    )
                )
                self.event_bus.publish(
                    SystemEvent(
                        event_type="validation_failed",
                        entity_type="task",
                        entity_id=task_id,
                        payload={
                            "task_id": task_id,
                            "iteration": review.iteration_number,
                            "feedback": review.feedback,
                        },
                    )
                )

            # Write Memory entry (REQ-VAL-MEM-001)
            if self.memory and task.ticket_id:
                self._record_validation_memory(review, task.ticket_id)

            # Check for repeated failures (REQ-VAL-DIAG-001)
            self._check_repeated_failures(task_id, session)

            return True

    # -------------------------------------------------------------------------
    # Validator Spawning
    # -------------------------------------------------------------------------

    def spawn_validator(
        self,
        task_id: str,
        commit_sha: Optional[str] = None,
    ) -> Optional[str]:
        """Spawn validator agent for task (REQ-VAL-LC-001).

        Args:
            task_id: Task ID to spawn validator for
            commit_sha: Optional Git commit SHA for validator to review

        Returns:
            Validator agent ID if successful, None if task not found or already has validator
        """
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return None

            # Check if already has active validator for this iteration
            if task_id in self._active_validators:
                return None  # Already has validator

            # Check if validation enabled
            if not task.validation_enabled:
                return None

            # Spawn validator agent via agent registry
            validator = self.agent_registry.register_agent(
                agent_type="validator",
                phase_id=task.phase_id,  # Validator for same phase
                capabilities=["validation", "code_review", "testing"],
                capacity=1,
                status="idle",
                tags=["validator"],
            )

            # Track active validator
            self._active_validators[task_id] = validator.id

            # Transition to validation_in_progress
            self.transition_to_validation_in_progress(task_id, validator.id)

            return validator.id

    # -------------------------------------------------------------------------
    # Review Handling
    # -------------------------------------------------------------------------

    def give_review(
        self,
        task_id: str,
        validator_agent_id: str,
        validation_passed: bool,
        feedback: str,
        evidence: Optional[Dict] = None,
        recommendations: Optional[List[str]] = None,
    ) -> Dict[str, any]:
        """Submit validation review (REQ-VAL-SM-002, REQ-VAL-SEC-001).

        Preconditions:
            - Caller's agent_type must be "validator" (REQ-VAL-SEC-001)
            - Task must be in validation_in_progress state
            - feedback must be non-empty if validation_passed == False

        Args:
            task_id: Task ID being reviewed
            validator_agent_id: ID of validator agent submitting review
            validation_passed: Whether validation passed
            feedback: Feedback text (required)
            evidence: Optional evidence dict
            recommendations: Optional list of recommendations

        Returns:
            Dict with status ("completed" or "needs_work"), message, and iteration

        Raises:
            PermissionError: If validator_agent_id is not a validator agent
            ValueError: If task not in validation_in_progress or feedback empty
        """
        with self.db.get_session() as session:
            # Verify validator agent
            validator = session.get(Agent, validator_agent_id)
            if not validator or validator.agent_type != "validator":
                raise PermissionError(
                    f"Only validator agents may call give_review. "
                    f"Agent {validator_agent_id} has type {validator.agent_type if validator else 'not_found'}"
                )

            # Get task
            task = session.get(Task, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")

            # Verify task is in validation_in_progress
            if task.status != ValidationState.VALIDATION_IN_PROGRESS:
                raise ValueError(
                    f"Task {task_id} must be in validation_in_progress state, "
                    f"but is in {task.status}"
                )

            # Verify feedback present if failed
            if not validation_passed and not feedback:
                raise ValueError("feedback required when validation_passed=False")

            # Create review
            review = ValidationReview(
                id=str(uuid4()),
                task_id=task_id,
                validator_agent_id=validator_agent_id,
                iteration_number=task.validation_iteration,
                validation_passed=validation_passed,
                feedback=feedback,
                evidence=evidence,
                recommendations=recommendations,
                created_at=utc_now(),
            )

            # Apply transition based on validation result
            if validation_passed:
                self.transition_to_done(task_id, review)
                status = "completed"
                message = "Validation passed"
            else:
                self.transition_to_needs_work(task_id, review)
                status = "needs_work"
                message = "Validation failed; feedback recorded"

            return {
                "status": status,
                "message": message,
                "iteration": task.validation_iteration,
            }

    # -------------------------------------------------------------------------
    # Feedback Delivery
    # -------------------------------------------------------------------------

    def send_feedback(
        self,
        agent_id: str,
        feedback: str,
    ) -> bool:
        """Deliver validation feedback to originating agent (REQ-VAL-LC-002).

        Uses transport-agnostic delivery (EventBus in this implementation).

        Args:
            agent_id: ID of agent to send feedback to
            feedback: Feedback text to deliver

        Returns:
            True if agent found, False otherwise
        """
        with self.db.get_session() as session:
            agent = session.get(Agent, agent_id)
            if not agent:
                return False

            # Deliver feedback via EventBus (transport-agnostic)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="agent.validation_feedback",
                        entity_type="agent",
                        entity_id=agent_id,
                        payload={
                            "agent_id": agent_id,
                            "feedback": feedback,
                            "timestamp": utc_now().isoformat(),
                        },
                    )
                )

            return True

    # -------------------------------------------------------------------------
    # Status Queries
    # -------------------------------------------------------------------------

    def get_validation_status(self, task_id: str) -> Optional[Dict[str, any]]:
        """Get validation status for a task (REQ-VAL-API).

        Args:
            task_id: Task ID to query

        Returns:
            Dict with task_id, state, iteration, review_done, last_feedback
            or None if task not found
        """
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                return None

            # Compute current validation state from task status
            state = self._derive_validation_state(task)

            return {
                "task_id": task_id,
                "state": state,
                "iteration": task.validation_iteration,
                "review_done": task.review_done,
                "last_feedback": task.last_validation_feedback,
            }

    def _derive_validation_state(self, task: Task) -> str:
        """Derive validation state from task status.

        Args:
            task: Task to derive state for

        Returns:
            Validation state string
        """
        # Map task status to validation state
        status_map = {
            "pending": ValidationState.PENDING,
            "assigned": ValidationState.ASSIGNED,
            "running": ValidationState.IN_PROGRESS,
            "under_review": ValidationState.UNDER_REVIEW,
            "validation_in_progress": ValidationState.VALIDATION_IN_PROGRESS,
            "needs_work": ValidationState.NEEDS_WORK,
            "completed": ValidationState.DONE,
            "failed": ValidationState.FAILED,
        }
        return status_map.get(task.status, task.status)

    # -------------------------------------------------------------------------
    # Integration Helpers
    # -------------------------------------------------------------------------

    def _record_validation_memory(
        self,
        review: ValidationReview,
        ticket_id: str,
    ) -> None:
        """Record validation outcome in Memory System (REQ-VAL-MEM-001).

        Args:
            review: ValidationReview to record
            ticket_id: Ticket ID for memory linking
        """
        if not self.memory:
            return

        # Create memory entry for validation outcome
        try:
            with self.db.get_session() as session:
                self.memory.store_execution(
                    session=session,
                    task_id=review.task_id,
                    execution_summary=f"Validation iteration {review.iteration_number}: "
                    f"{'PASSED' if review.validation_passed else 'FAILED'}. "
                    f"Feedback: {review.feedback}",
                    success=review.validation_passed,
                    error_patterns=(
                        [review.feedback] if not review.validation_passed else None
                    ),
                )
                session.commit()
        except Exception as e:
            # Log but don't fail validation if memory write fails
            logger.warning("Failed to record validation memory", error=str(e))

    def _check_repeated_failures(self, task_id: str, session) -> None:
        """Check for repeated validation failures and spawn Diagnosis if needed (REQ-VAL-DIAG-001).

        Args:
            task_id: Task ID to check
            session: Database session
        """
        if not self.diagnostic:
            return

        task = session.get(Task, task_id)
        if not task:
            return

        # Get all validation reviews for this task
        reviews = (
            session.query(ValidationReview)
            .filter(ValidationReview.task_id == task_id)
            .order_by(ValidationReview.iteration_number.desc())
            .all()
        )

        # Count consecutive failures
        consecutive_failures = 0
        for review in reviews:
            if not review.validation_passed:
                consecutive_failures += 1
            else:
                break  # Stop counting at first pass

        # Spawn Diagnosis Agent if threshold met (default: 2)
        DIAG_VALIDATION_FAILURES_THRESHOLD = 2  # From config (REQ-VAL-DIAG-001)
        if consecutive_failures >= DIAG_VALIDATION_FAILURES_THRESHOLD:
            try:
                # Spawn diagnostic agent for the workflow (async call in sync context)
                import asyncio

                try:
                    asyncio.get_running_loop()
                    # Event loop exists, create task
                    asyncio.create_task(
                        self.diagnostic.spawn_diagnostic_agent(
                            workflow_id=task.ticket_id,
                            context={
                                "trigger": "repeated_validation_failures",
                                "task_id": task_id,
                                "consecutive_failures": consecutive_failures,
                                "last_feedback": task.last_validation_feedback,
                            },
                            max_tasks=5,
                        )
                    )
                    # Don't await in sync context - fire and forget
                    diagnostic_run = None  # Will be None, but task is running
                    logger.warning(
                        "Diagnosis spawned for repeated validation failures",
                        consecutive_failures=consecutive_failures,
                        task_id=task_id,
                        mode="async_task",
                    )
                except RuntimeError:
                    # No event loop, use asyncio.run()
                    diagnostic_run = asyncio.run(
                        self.diagnostic.spawn_diagnostic_agent(
                            workflow_id=task.ticket_id,
                            context={
                                "trigger": "repeated_validation_failures",
                                "task_id": task_id,
                                "consecutive_failures": consecutive_failures,
                                "last_feedback": task.last_validation_feedback,
                            },
                            max_tasks=5,
                        )
                    )
                    logger.warning(
                        "Diagnosis spawned for repeated validation failures",
                        consecutive_failures=consecutive_failures,
                        task_id=task_id,
                        diagnostic_run_id=str(diagnostic_run.id),
                    )
            except Exception as e:
                logger.warning("Failed to spawn diagnostic agent", error=str(e))

    def check_validator_timeouts(self, timeout_minutes: int = 10) -> None:
        """Check for validator timeouts and handle (REQ-VAL-DIAG-002).

        Args:
            timeout_minutes: Validator timeout threshold (default: 10 minutes)
        """
        if not self.diagnostic:
            return

        utc_now() - timedelta(minutes=timeout_minutes)

        with self.db.get_session() as session:
            for task_id, validator_id in list(self._active_validators.items()):
                task = session.get(Task, task_id)
                if not task:
                    continue

                # Check if task entered validation_in_progress before timeout threshold
                # (We'd need started_at timestamp for validation, but for now check status)
                if task.status == ValidationState.VALIDATION_IN_PROGRESS:
                    # Get validator agent
                    validator = session.get(Agent, validator_id)
                    if validator and validator.last_heartbeat:
                        elapsed = utc_now() - validator.last_heartbeat
                        if elapsed.total_seconds() > (timeout_minutes * 60):
                            # Validator timed out
                            logger.warning(
                                "Validator timeout detected",
                                task_id=task_id,
                                validator_id=validator_id,
                                timeout_minutes=timeout_minutes,
                            )

                            # Spawn Diagnosis Agent focused on timeout (REQ-VAL-DIAG-002)
                            try:
                                import asyncio

                                try:
                                    asyncio.get_running_loop()
                                    # Event loop exists, create task
                                    asyncio.create_task(
                                        self.diagnostic.spawn_diagnostic_agent(
                                            workflow_id=task.ticket_id,
                                            context={
                                                "trigger": "validation_timeout",
                                                "task_id": task_id,
                                                "validator_agent_id": validator_id,
                                                "timeout_minutes": timeout_minutes,
                                            },
                                            max_tasks=5,
                                        )
                                    )
                                    # Don't await in sync context - fire and forget
                                    diagnostic_run = None
                                    logger.warning(
                                        "Diagnosis spawned for validation timeout",
                                        task_id=task_id,
                                        mode="async_task",
                                    )
                                except RuntimeError:
                                    # No event loop, use asyncio.run()
                                    diagnostic_run = asyncio.run(
                                        self.diagnostic.spawn_diagnostic_agent(
                                            workflow_id=task.ticket_id,
                                            context={
                                                "trigger": "validation_timeout",
                                                "task_id": task_id,
                                                "validator_agent_id": validator_id,
                                                "timeout_minutes": timeout_minutes,
                                            },
                                            max_tasks=5,
                                        )
                                    )
                                    logger.warning(
                                        "Diagnosis spawned for validation timeout",
                                        task_id=task_id,
                                        diagnostic_run_id=str(diagnostic_run.id),
                                    )
                            except Exception as e:
                                logger.warning(
                                    "Failed to spawn diagnostic agent", error=str(e)
                                )

                            # Clear active validator
                            self._active_validators.pop(task_id, None)

                            # Mark task as failed due to timeout
                            task.status = ValidationState.FAILED
                            task.error_message = (
                                f"Validation timeout after {timeout_minutes} minutes"
                            )
                            session.commit()
