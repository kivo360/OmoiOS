"""Task queue service for managing task assignment and retrieval."""

from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import or_, select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from omoi_os.logging import get_logger
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_scorer import TaskScorer

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from omoi_os.services.event_bus import EventBusService

logger = get_logger(__name__)


async def generate_task_title(
    task_id: str,
    db: "DatabaseService",
    task_type: str,
    description: Optional[str] = None,
    context: Optional[str] = None,
) -> Optional[str]:
    """
    Generate and update a task's title using the TitleGenerationService.

    This is an async helper that can be called after task creation to
    generate a human-readable title without blocking the main flow.

    Args:
        task_id: UUID of the task to update
        db: DatabaseService instance
        task_type: The task type (e.g., "analyze_requirements")
        description: Optional existing task description
        context: Optional additional context for title generation

    Returns:
        Generated title string, or None if generation failed
    """
    try:
        from omoi_os.services.title_generation_service import get_title_generation_service

        title_service = get_title_generation_service()
        result = await title_service.generate_title_and_description(
            task_type=task_type,
            existing_description=description,
            context=context,
        )

        # Update the task with the generated title and description
        with db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.title = result.title
                # Only update description if we generated one and task doesn't have one
                if result.description and not task.description:
                    task.description = result.description
                session.commit()
                logger.info(
                    "Generated title for task",
                    task_id=task_id,
                    title=result.title,
                )
                return result.title

    except Exception as e:
        logger.warning(
            "Failed to generate title for task",
            task_id=task_id,
            error=str(e),
        )

    return None


class TaskQueueService:
    """Manages task queue operations: enqueue, retrieve, assign, update."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional["EventBusService"] = None,
    ):
        """
        Initialize task queue service.

        Args:
            db: DatabaseService instance
            event_bus: Optional EventBusService for real-time updates
        """
        self.db = db
        self.scorer = TaskScorer(db)
        self.event_bus = event_bus

    def _publish_event(
        self,
        event_type: str,
        task: Task,
        extra_payload: Optional[dict] = None,
    ) -> None:
        """Publish task event to event bus."""
        if not self.event_bus:
            return

        try:
            from omoi_os.services.event_bus import SystemEvent

            payload = {
                "task_id": str(task.id),
                "ticket_id": task.ticket_id,
                "phase_id": task.phase_id,
                "task_type": task.task_type,
                "status": task.status,
                "priority": task.priority,
            }
            if extra_payload:
                payload.update(extra_payload)

            event = SystemEvent(
                event_type=event_type,
                entity_type="task",
                entity_id=str(task.id),
                payload=payload,
            )
            self.event_bus.publish(event)
            logger.debug(f"Published {event_type} for task {task.id}")
        except Exception as e:
            logger.warning(f"Failed to publish event {event_type}: {e}")

    def enqueue_task(
        self,
        ticket_id: str,
        phase_id: str,
        task_type: str,
        description: str,
        priority: str,
        dependencies: dict | None = None,
        session: Optional["Session"] = None,
        title: Optional[str] = None,
    ) -> Task:
        """
        Add a task to the queue.

        Args:
            ticket_id: UUID of the parent ticket
            phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")
            task_type: Type of task (e.g., "implement_feature")
            description: Task description
            priority: Task priority (CRITICAL, HIGH, MEDIUM, LOW)
            dependencies: Optional dependencies dict: {"depends_on": ["task_id_1", "task_id_2"]}
            session: Optional database session to use. If not provided, creates a new session.
            title: Optional human-readable title. If not provided, can be generated later
                   using generate_task_title().

        Returns:
            Created Task object
        """
        if session is not None:
            # Use provided session
            task = Task(
                ticket_id=ticket_id,
                phase_id=phase_id,
                task_type=task_type,
                title=title,
                description=description,
                priority=priority,
                status="pending",
                dependencies=dependencies,
            )
            session.add(task)
            session.flush()
            session.refresh(task)

            # Compute initial score (REQ-TQM-PRI-002)
            task.score = self.scorer.compute_score(task)

            # Don't commit here - let the caller handle it
            session.refresh(task)

            # Publish event (after flush so task has ID)
            self._publish_event("TASK_CREATED", task, {"description": description})
            return task
        else:
            # Create new session (original behavior)
            with self.db.get_session() as session:
                task = Task(
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                    task_type=task_type,
                    title=title,
                    description=description,
                    priority=priority,
                    status="pending",
                    dependencies=dependencies,
                )
                session.add(task)
                session.flush()
                session.refresh(task)

                # Compute initial score (REQ-TQM-PRI-002)
                task.score = self.scorer.compute_score(task)

                session.commit()
                session.refresh(task)
                # Expunge the task so it can be used outside the session
                session.expunge(task)

                # Publish event after commit
                self._publish_event("TASK_CREATED", task, {"description": description})
                return task

    def get_next_task(
        self, phase_id: Optional[str] = None, agent_capabilities: Optional[List[str]] = None
    ) -> Task | None:
        """
        Get highest-scored pending task for a phase that has all dependencies completed.
        Uses dynamic scoring per REQ-TQM-PRI-002.
        Verifies capability matching per REQ-TQM-ASSIGN-001.

        IMPORTANT: This method atomically claims the task by setting status to 'claiming'
        to prevent duplicate sandbox spawns from race conditions.

        Args:
            phase_id: Phase identifier to filter by (None = any phase)
            agent_capabilities: Optional list of agent capabilities for matching (REQ-TQM-ASSIGN-001)

        Returns:
            Task object or None if no pending tasks with completed dependencies and matching capabilities
        """
        with self.db.get_session() as session:
            # Only get tasks that are truly pending (not already being claimed)
            # Also exclude tasks that already have a sandbox_id (prevents duplicate spawns)
            query = session.query(Task).filter(
                Task.status == "pending",
                Task.sandbox_id.is_(None),  # Exclude tasks with existing sandbox
            )
            if phase_id is not None:
                query = query.filter(Task.phase_id == phase_id)
            tasks = query.all()
            if not tasks:
                return None

            # Filter out tasks with incomplete dependencies and capability mismatches
            available_tasks = []
            for task in tasks:
                if not self._check_dependencies_complete(session, task):
                    continue

                # Check capability matching (REQ-TQM-ASSIGN-001)
                if agent_capabilities is not None and not self._check_capability_match(
                    task, agent_capabilities
                ):
                    continue  # Skip tasks that don't match capabilities

                # Compute and update score (REQ-TQM-PRI-002)
                task.score = self.scorer.compute_score(task)
                available_tasks.append(task)

            if not available_tasks:
                return None

            # Sort by score descending (REQ-TQM-PRI-002)
            task = max(available_tasks, key=lambda t: t.score)

            # ATOMIC CLAIM: Use SELECT ... FOR UPDATE SKIP LOCKED to prevent race conditions
            # This ensures only one orchestrator can claim this task
            from sqlalchemy import text

            # Try to atomically claim the task by updating status to 'claiming'
            # Using row-level lock to prevent duplicate claims
            result = session.execute(
                text("""
                    UPDATE tasks
                    SET status = 'claiming', score = :score
                    WHERE id = :task_id
                    AND status = 'pending'
                    AND sandbox_id IS NULL
                    RETURNING id
                """),
                {"task_id": str(task.id), "score": task.score}
            )
            claimed_row = result.fetchone()
            session.commit()

            if not claimed_row:
                # Another process claimed this task, try again with next available
                logger.debug(
                    f"Task {task.id} was claimed by another process, skipping"
                )
                return None

            # Refresh to get latest state after our update
            session.refresh(task)

            # Expunge so it can be used outside the session
            session.expunge(task)
            return task

    def get_ready_tasks(
        self,
        phase_id: Optional[str] = None,
        limit: int = 10,
        agent_capabilities: Optional[List[str]] = None,
    ) -> list[Task]:
        """
        Get multiple ready tasks for parallel execution (DAG batching).
        Uses dynamic scoring per REQ-TQM-PRI-002.
        Verifies capability matching per REQ-TQM-ASSIGN-001.

        Args:
            phase_id: Optional phase identifier to filter by
            limit: Maximum number of tasks to return
            agent_capabilities: Optional list of agent capabilities for matching (REQ-TQM-ASSIGN-001)

        Returns:
            List of Task objects ready for execution, sorted by score descending
        """
        with self.db.get_session() as session:
            query = session.query(Task).filter(Task.status == "pending")
            if phase_id:
                query = query.filter(Task.phase_id == phase_id)
            tasks = query.all()

            if not tasks:
                return []

            # Filter out tasks with incomplete dependencies and capability mismatches
            available_tasks = []
            for task in tasks:
                if not self._check_dependencies_complete(session, task):
                    continue

                # Check capability matching (REQ-TQM-ASSIGN-001)
                if agent_capabilities is not None and not self._check_capability_match(
                    task, agent_capabilities
                ):
                    continue  # Skip tasks that don't match capabilities

                # Compute and update score (REQ-TQM-PRI-002)
                task.score = self.scorer.compute_score(task)
                available_tasks.append(task)

            # Sort by score descending (REQ-TQM-PRI-002)
            available_tasks.sort(key=lambda t: t.score, reverse=True)

            # Take top N tasks
            batch = available_tasks[:limit]

            # Update scores in database
            for task in batch:
                session.query(Task).filter(Task.id == task.id).update(
                    {"score": task.score}
                )
            session.commit()
            # Refresh all tasks to ensure all attributes are loaded
            for task in batch:
                session.refresh(task)

            # Expunge all tasks for use outside session
            for task in batch:
                session.expunge(task)

            return batch

    def assign_task(self, task_id: str, agent_id: str) -> None:
        """
        Assign a task to an agent.

        Transitions task from 'claiming' to 'assigned' status.

        Args:
            task_id: UUID of the task
            agent_id: UUID of the agent
        """
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                # Validate task is in expected state (pending or claiming)
                if task.status not in ("pending", "claiming"):
                    logger.warning(
                        f"Task {task_id} has unexpected status {task.status} during assignment, "
                        f"expected 'pending' or 'claiming'"
                    )
                task.assigned_agent_id = agent_id
                task.status = "assigned"
                session.commit()
                session.refresh(task)

                # Publish assignment event
                self._publish_event(
                    "TASK_ASSIGNED",
                    task,
                    {"agent_id": agent_id},
                )

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: dict | None = None,
        error_message: str | None = None,
        conversation_id: str | None = None,
        persistence_dir: str | None = None,
    ) -> None:
        """
        Update task status and result.

        Args:
            task_id: UUID of the task
            status: New status (running, completed, failed)
            result: Optional task result dictionary
            error_message: Optional error message if failed
            conversation_id: Optional OpenHands conversation ID
            persistence_dir: Optional OpenHands conversation persistence directory
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                old_status = task.status
                task.status = status
                if result:
                    task.result = result
                if error_message:
                    task.error_message = error_message
                if conversation_id:
                    task.conversation_id = conversation_id
                if persistence_dir:
                    task.persistence_dir = persistence_dir
                if status == "running" and not task.started_at:
                    task.started_at = utc_now()
                elif status in ("completed", "failed") and not task.completed_at:
                    task.completed_at = utc_now()

                session.commit()
                session.refresh(task)

                # Publish status change event
                event_type = {
                    "running": "TASK_STARTED",
                    "completed": "TASK_COMPLETED",
                    "failed": "TASK_FAILED",
                    "cancelled": "TASK_CANCELLED",
                }.get(status, "TASK_STATUS_CHANGED")

                self._publish_event(
                    event_type,
                    task,
                    {
                        "old_status": old_status,
                        "error_message": error_message,
                        "has_result": result is not None,
                    },
                )

    def get_assigned_tasks(
        self, agent_id: str, sandbox_id: Optional[str] = None
    ) -> list[Task]:
        """
        Get all tasks assigned to a specific agent or sandbox.

        Supports both legacy (assigned_agent_id) and sandbox (sandbox_id) modes.

        Args:
            agent_id: UUID of the agent
            sandbox_id: Optional sandbox ID for sandbox mode queries

        Returns:
            List of Task objects assigned to the agent or sandbox
        """
        with self.db.get_session() as session:
            # Build ownership filter supporting both modes
            if sandbox_id:
                ownership_filter = Task.sandbox_id == sandbox_id
            else:
                ownership_filter = Task.assigned_agent_id == agent_id

            tasks = (
                session.query(Task)
                .filter(
                    ownership_filter,
                    Task.status.in_(["claiming", "assigned", "running"]),
                )
                .all()
            )
            # Expunge all tasks so they can be used outside the session
            for task in tasks:
                session.expunge(task)
            return tasks

    def _check_dependencies_complete(self, session, task: Task) -> bool:
        """
        Check if all dependencies for a task are completed.

        Args:
            session: Database session
            task: Task to check dependencies for

        Returns:
            True if all dependencies are completed, False otherwise
        """
        if not task.dependencies:
            return True

        depends_on = task.dependencies.get("depends_on", [])
        if not depends_on:
            return True

        # Check if all dependency tasks are completed
        dependency_tasks = session.query(Task).filter(Task.id.in_(depends_on)).all()

        # If we can't find all dependencies, consider them incomplete
        if len(dependency_tasks) != len(depends_on):
            return False

        # All dependencies must be completed
        return all(dep_task.status == "completed" for dep_task in dependency_tasks)

    def _check_capability_match(
        self, task: Task, agent_capabilities: List[str]
    ) -> bool:
        """
        Check if agent capabilities match task requirements per REQ-TQM-ASSIGN-001.

        Args:
            task: Task to check capabilities for
            agent_capabilities: List of agent capabilities

        Returns:
            True if agent has all required capabilities, False otherwise
        """
        if not task.required_capabilities:
            return True  # No requirements = any agent can handle

        required = set(task.required_capabilities)
        agent_caps = set(agent_capabilities or [])

        # All required capabilities must be present
        if not required.issubset(agent_caps):
            missing = required - agent_caps
            logger.warning(
                f"Capability mismatch for task {task.id}: "
                f"missing {missing}, agent has {agent_capabilities}"
            )
            return False

        return True

    def check_dependencies_complete(self, task_id: str) -> bool:
        """
        Check if all dependencies for a task are completed.

        Args:
            task_id: UUID of the task

        Returns:
            True if all dependencies are completed, False otherwise
        """
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False
            return self._check_dependencies_complete(session, task)

    def get_blocked_tasks(self, task_id: str) -> list[Task]:
        """
        Get all tasks that are blocked by this task (i.e., tasks that depend on this task).

        Args:
            task_id: UUID of the task

        Returns:
            List of Task objects that depend on this task
        """
        with self.db.get_session() as session:
            # Find all tasks that have this task_id in their dependencies
            all_tasks = session.query(Task).all()
            blocked_tasks = []

            for task in all_tasks:
                if task.dependencies:
                    depends_on = task.dependencies.get("depends_on", [])
                    if task_id in depends_on:
                        blocked_tasks.append(task)

            # Expunge tasks so they can be used outside the session
            for task in blocked_tasks:
                session.expunge(task)
            return blocked_tasks

    def detect_circular_dependencies(
        self, task_id: str, depends_on: list[str], visited: list[str] | None = None
    ) -> list[str] | None:
        """
        Detect circular dependencies using DFS.

        Args:
            task_id: UUID of the task being checked
            depends_on: List of task IDs this task depends on
            visited: List of visited task IDs in order (for recursion)

        Returns:
            List of task IDs forming a cycle, or None if no cycle
        """
        if visited is None:
            visited = []

        if task_id in visited:
            # Found a cycle - return the cycle starting from where we first saw this task
            cycle_start = visited.index(task_id)
            return visited[cycle_start:] + [task_id]

        visited.append(task_id)

        with self.db.get_session() as session:
            for dep_id in depends_on:
                dep_task = session.query(Task).filter(Task.id == dep_id).first()
                if dep_task and dep_task.dependencies:
                    dep_depends_on = dep_task.dependencies.get("depends_on", [])
                    cycle = self.detect_circular_dependencies(
                        dep_id, dep_depends_on, visited.copy()
                    )
                    if cycle:
                        return cycle

        return None

    def should_retry(self, task_id: str) -> bool:
        """
        Check if a failed task should be retried.

        Args:
            task_id: UUID of the task to check

        Returns:
            True if task should be retried, False otherwise
        """
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False

            # Only retry failed tasks
            if task.status != "failed":
                return False

            # Check if we haven't exceeded max retries
            return task.retry_count < task.max_retries

    def increment_retry(self, task_id: str) -> bool:
        """
        Increment retry count and reset status to pending.

        Args:
            task_id: UUID of the task to retry

        Returns:
            True if retry was scheduled, False if max retries exceeded
        """
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False

            # Check if we can retry
            if task.retry_count >= task.max_retries:
                return False

            # Increment retry count and reset status
            task.retry_count += 1
            task.status = "pending"
            task.error_message = None  # Clear previous error message
            # Clear appropriate assignment based on execution mode
            if task.sandbox_id:
                task.sandbox_id = None  # Clear sandbox for retry
            else:
                task.assigned_agent_id = None  # Clear legacy assignment

            session.commit()
            return True

    def get_retryable_tasks(self, phase_id: str | None = None) -> list[Task]:
        """
        Get all tasks that can be retried (failed tasks that haven't exceeded max retries).

        Args:
            phase_id: Optional phase ID to filter by

        Returns:
            List of retryable Task objects
        """
        with self.db.get_session() as session:
            query = session.query(Task).filter(Task.status == "failed")

            if phase_id:
                query = query.filter(Task.phase_id == phase_id)

            tasks = query.all()

            # Filter by retry count vs max retries
            retryable_tasks = [
                task for task in tasks if task.retry_count < task.max_retries
            ]

            # Expunge tasks so they can be used outside the session
            for task in retryable_tasks:
                session.expunge(task)

            return retryable_tasks

    def is_retryable_error(self, error_message: str | None) -> bool:
        """
        Check if an error message indicates a retryable error.

        Args:
            error_message: Error message to analyze

        Returns:
            True if error is retryable, False if it's a permanent failure
        """
        if not error_message:
            return True  # No error message, assume retryable

        error_lower = error_message.lower()

        # Permanent errors that should not be retried
        permanent_error_patterns = [
            "permission denied",
            "access denied",
            "authentication failed",
            "authorization failed",
            "syntax error",
            "invalid argument",
            "not found",
            "does not exist",
            "already exists",
            "duplicate key",
            "constraint violation",
            "immutable",
            "read-only",
            "quota exceeded",
            "rate limit exceeded",
        ]

        for pattern in permanent_error_patterns:
            if pattern in error_lower:
                return False

        # Network-related and temporary errors are retryable
        retryable_patterns = [
            "connection",
            "timeout",
            "network",
            "temporary",
            "unavailable",
            "retryable",
            "transient",
            "intermittent",
        ]

        for pattern in retryable_patterns:
            if pattern in error_lower:
                return True

        # Default to retryable for unknown errors
        return True

    # Task Timeout & Cancellation Methods (Agent D)

    def check_task_timeout(self, task_id: str) -> bool:
        """
        Check if a task has exceeded its timeout.

        Args:
            task_id: UUID of the task to check

        Returns:
            True if task has timed out, False otherwise
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False

            # Only check running tasks with timeout set
            if task.status != "running" or not task.timeout_seconds:
                return False

            # Check if started_at is set
            if not task.started_at:
                return False

            # Calculate elapsed time
            elapsed_seconds = (utc_now() - task.started_at).total_seconds()
            return elapsed_seconds > task.timeout_seconds

    def cancel_task(self, task_id: str, reason: str = "cancelled_by_request") -> bool:
        """
        Cancel a running task.

        Args:
            task_id: UUID of the task to cancel
            reason: Reason for cancellation

        Returns:
            True if task was cancelled, False if task not found or not cancellable
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False

            # Only cancel running tasks
            if task.status not in ["assigned", "running"]:
                return False

            # Update task status
            task.status = "failed"
            task.error_message = f"Task cancelled: {reason}"
            task.completed_at = utc_now()

            session.commit()
            return True

    def get_timed_out_tasks(self) -> list[Task]:
        """
        Get all tasks that have exceeded their timeout.

        Returns:
            List of timed-out Task objects
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            # Get all running tasks with timeout set
            tasks = (
                session.query(Task)
                .filter(Task.status == "running", Task.timeout_seconds.isnot(None))
                .all()
            )

            timed_out_tasks = []
            for task in tasks:
                if task.started_at:
                    elapsed_seconds = (utc_now() - task.started_at).total_seconds()
                    if elapsed_seconds > task.timeout_seconds:
                        timed_out_tasks.append(task)

            # Expunge tasks so they can be used outside the session
            for task in timed_out_tasks:
                session.expunge(task)

            return timed_out_tasks

    def mark_task_timeout(self, task_id: str, reason: str = "timeout_exceeded") -> bool:
        """
        Mark a task as failed due to timeout.

        Args:
            task_id: UUID of the task to mark as timed out
            reason: Timeout reason

        Returns:
            True if task was marked as timed out, False if task not found
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return False

            # Only mark running tasks as timed out
            if task.status != "running":
                return False

            # Calculate elapsed time for debugging
            elapsed_seconds = 0
            if task.started_at:
                elapsed_seconds = (utc_now() - task.started_at).total_seconds()

            # Update task status
            task.status = "failed"
            task.error_message = (
                f"Task timed out after {elapsed_seconds:.1f}s: {reason}"
            )
            task.completed_at = utc_now()

            session.commit()
            return True

    def get_cancellable_tasks(
        self, agent_id: str | None = None, sandbox_id: str | None = None
    ) -> list[Task]:
        """
        Get all tasks that can be cancelled.

        Supports both legacy (agent_id) and sandbox (sandbox_id) filtering.

        Args:
            agent_id: Optional agent ID to filter by (legacy mode)
            sandbox_id: Optional sandbox ID to filter by (sandbox mode)

        Returns:
            List of cancellable Task objects
        """
        with self.db.get_session() as session:
            query = session.query(Task).filter(Task.status.in_(["assigned", "running"]))

            if sandbox_id:
                query = query.filter(Task.sandbox_id == sandbox_id)
            elif agent_id:
                query = query.filter(Task.assigned_agent_id == agent_id)

            tasks = query.all()

            # Expunge tasks so they can be used outside the session
            for task in tasks:
                session.expunge(task)

            return tasks

    def get_task_elapsed_time(self, task_id: str) -> float | None:
        """
        Get the elapsed time for a running task.

        Args:
            task_id: UUID of the task

        Returns:
            Elapsed time in seconds, or None if task not found or not running
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task or task.status != "running" or not task.started_at:
                return None

            return (utc_now() - task.started_at).total_seconds()

    def get_task_timeout_status(self, task_id: str) -> dict:
        """
        Get comprehensive timeout status for a task.

        Args:
            task_id: UUID of the task

        Returns:
            Dictionary with timeout status information
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return {"exists": False}

            elapsed_seconds = 0
            is_timed_out = False
            time_remaining = None

            if task.started_at:
                elapsed_seconds = (utc_now() - task.started_at).total_seconds()

                if task.timeout_seconds:
                    time_remaining = max(0, task.timeout_seconds - elapsed_seconds)
                    is_timed_out = elapsed_seconds > task.timeout_seconds

            return {
                "exists": True,
                "status": task.status,
                "timeout_seconds": task.timeout_seconds,
                "elapsed_seconds": elapsed_seconds,
                "time_remaining": time_remaining,
                "is_timed_out": is_timed_out,
                "can_cancel": task.status in ["assigned", "running"],
            }

    def cleanup_stale_claiming_tasks(
        self, stale_threshold_seconds: int = 60
    ) -> list[dict]:
        """
        Clean up tasks stuck in 'claiming' status.

        Tasks in 'claiming' status should transition to 'assigned' within seconds.
        If they've been claiming for too long, the orchestrator likely crashed
        after claiming but before assigning. Reset them to 'pending' for retry.

        Args:
            stale_threshold_seconds: Seconds after which a claiming task is considered stale

        Returns:
            List of dicts with task info for each cleaned up task
        """
        from datetime import timedelta
        from omoi_os.utils.datetime import utc_now

        stale_cutoff = utc_now() - timedelta(seconds=stale_threshold_seconds)
        cleaned_tasks = []

        with self.db.get_session() as session:
            # Find tasks stuck in 'claiming' status
            tasks = (
                session.query(Task)
                .filter(
                    Task.status == "claiming",
                    or_(
                        Task.created_at < stale_cutoff,
                        # Also check updated_at if available
                    ),
                )
                .all()
            )

            for task in tasks:
                task_info = {
                    "task_id": str(task.id),
                    "task_type": task.task_type,
                    "description": task.description[:50] if task.description else None,
                    "created_at": str(task.created_at),
                }

                # Reset to pending so it can be claimed again
                task.status = "pending"
                cleaned_tasks.append(task_info)

            if cleaned_tasks:
                session.commit()
                logger.info(
                    f"Reset {len(cleaned_tasks)} stale claiming tasks to pending"
                )

        return cleaned_tasks

    def get_stale_assigned_tasks(
        self, stale_threshold_minutes: int = 3
    ) -> list[Task]:
        """
        Get tasks stuck in 'assigned' or 'claiming' status for too long.

        Tasks that have been assigned but never transitioned to 'running' are
        likely orphaned (sandbox crashed before sending agent.started event).

        Args:
            stale_threshold_minutes: Minutes after which an assigned task is considered stale

        Returns:
            List of stale Task objects
        """
        from datetime import timedelta
        from omoi_os.utils.datetime import utc_now

        stale_cutoff = utc_now() - timedelta(minutes=stale_threshold_minutes)

        with self.db.get_session() as session:
            # Find tasks that:
            # 1. Are in 'assigned' status (or 'claiming' for longer than threshold)
            # 2. Have a sandbox_id (were assigned to a sandbox)
            # 3. Were created more than threshold ago
            tasks = (
                session.query(Task)
                .filter(
                    Task.status.in_(["assigned", "claiming"]),
                    Task.sandbox_id.isnot(None),
                    Task.created_at < stale_cutoff,
                )
                .all()
            )

            # Expunge tasks so they can be used outside the session
            for task in tasks:
                session.expunge(task)

            return tasks

    def cleanup_stale_assigned_tasks(
        self, stale_threshold_minutes: int = 3, dry_run: bool = False
    ) -> list[dict]:
        """
        Clean up tasks stuck in 'assigned' or 'claiming' status by marking them as failed.

        This handles cases where sandboxes crashed before sending any events
        (agent.started, agent.completed, etc.), leaving tasks orphaned.

        Args:
            stale_threshold_minutes: Minutes after which an assigned task is considered stale
            dry_run: If True, only report what would be cleaned up without making changes

        Returns:
            List of dicts with task info for each cleaned up task
        """
        from datetime import timedelta
        from omoi_os.utils.datetime import utc_now

        stale_cutoff = utc_now() - timedelta(minutes=stale_threshold_minutes)
        cleaned_tasks = []

        with self.db.get_session() as session:
            # Find stale assigned/claiming tasks
            # Include 'claiming' status for tasks where orchestrator crashed mid-claim
            tasks = (
                session.query(Task)
                .filter(
                    Task.status.in_(["assigned", "claiming"]),
                    Task.sandbox_id.isnot(None),
                    Task.created_at < stale_cutoff,
                )
                .all()
            )

            for task in tasks:
                task_info = {
                    "task_id": str(task.id),
                    "sandbox_id": task.sandbox_id,
                    "task_type": task.task_type,
                    "description": task.description[:50] if task.description else None,
                    "created_at": str(task.created_at),
                    "age_minutes": (utc_now() - task.created_at).total_seconds() / 60,
                }

                if not dry_run:
                    task.status = "failed"
                    task.error_message = (
                        f"Task stuck in assigned status for "
                        f"{task_info['age_minutes']:.1f} minutes. "
                        f"Sandbox may have crashed before starting."
                    )
                    task.completed_at = utc_now()

                cleaned_tasks.append(task_info)

            if not dry_run:
                session.commit()

        return cleaned_tasks

    # =========================================================================
    # ASYNC METHODS
    # =========================================================================
    # These async versions use the async database session for non-blocking I/O.
    # Per async_python_patterns.md, these should be used in async contexts
    # to avoid blocking the event loop.

    async def _check_dependencies_complete_async(
        self, session: AsyncSession, task: Task
    ) -> bool:
        """
        Async version: Check if all dependencies for a task are completed.

        Args:
            session: Async database session
            task: Task to check dependencies for

        Returns:
            True if all dependencies are completed, False otherwise
        """
        if not task.dependencies:
            return True

        depends_on = task.dependencies.get("depends_on", [])
        if not depends_on:
            return True

        # Check if all dependency tasks are completed
        result = await session.execute(
            select(Task).filter(Task.id.in_(depends_on))
        )
        dependency_tasks = result.scalars().all()

        # If we can't find all dependencies, consider them incomplete
        if len(dependency_tasks) != len(depends_on):
            return False

        # All dependencies must be completed
        return all(dep_task.status == "completed" for dep_task in dependency_tasks)

    async def get_ready_tasks_async(
        self,
        phase_id: Optional[str] = None,
        limit: int = 10,
        agent_capabilities: Optional[List[str]] = None,
    ) -> list[Task]:
        """
        Async version: Get multiple ready tasks for parallel execution.

        This is the async equivalent of get_ready_tasks(), using non-blocking
        database operations per async_python_patterns.md Section 3.

        Args:
            phase_id: Optional phase identifier to filter by
            limit: Maximum number of tasks to return
            agent_capabilities: Optional list of agent capabilities for matching

        Returns:
            List of Task objects ready for execution, sorted by score descending
        """
        async with self.db.get_async_session() as session:
            # Build query
            stmt = select(Task).filter(Task.status == "pending")
            if phase_id:
                stmt = stmt.filter(Task.phase_id == phase_id)

            result = await session.execute(stmt)
            tasks = result.scalars().all()

            if not tasks:
                return []

            # Filter out tasks with incomplete dependencies and capability mismatches
            available_tasks = []
            for task in tasks:
                if not await self._check_dependencies_complete_async(session, task):
                    continue

                # Check capability matching (REQ-TQM-ASSIGN-001)
                if agent_capabilities is not None and not self._check_capability_match(
                    task, agent_capabilities
                ):
                    continue

                # Compute and update score (REQ-TQM-PRI-002)
                task.score = self.scorer.compute_score(task)
                available_tasks.append(task)

            # Sort by score descending
            available_tasks.sort(key=lambda t: t.score, reverse=True)

            # Take top N tasks
            batch = available_tasks[:limit]

            # Update scores in database
            for task in batch:
                await session.execute(
                    update(Task).where(Task.id == task.id).values(score=task.score)
                )
            await session.commit()

            # Refresh all tasks
            for task in batch:
                await session.refresh(task)

            return batch

    async def get_next_task_async(
        self, phase_id: Optional[str] = None, agent_capabilities: Optional[List[str]] = None
    ) -> Task | None:
        """
        Async version: Get highest-scored pending task with atomic claim.

        This is the async equivalent of get_next_task(), using non-blocking
        database operations and atomic claim pattern.

        Args:
            phase_id: Phase identifier to filter by (None = any phase)
            agent_capabilities: Optional list of agent capabilities for matching

        Returns:
            Task object or None if no pending tasks available
        """
        async with self.db.get_async_session() as session:
            # Build query for pending tasks without sandbox
            stmt = select(Task).filter(
                Task.status == "pending",
                Task.sandbox_id.is_(None),
            )
            if phase_id is not None:
                stmt = stmt.filter(Task.phase_id == phase_id)

            result = await session.execute(stmt)
            tasks = result.scalars().all()

            if not tasks:
                return None

            # Filter out tasks with incomplete dependencies and capability mismatches
            available_tasks = []
            for task in tasks:
                if not await self._check_dependencies_complete_async(session, task):
                    continue

                if agent_capabilities is not None and not self._check_capability_match(
                    task, agent_capabilities
                ):
                    continue

                task.score = self.scorer.compute_score(task)
                available_tasks.append(task)

            if not available_tasks:
                return None

            # Sort by score descending
            task = max(available_tasks, key=lambda t: t.score)

            # Atomic claim using raw SQL
            claim_result = await session.execute(
                text("""
                    UPDATE tasks
                    SET status = 'claiming', score = :score
                    WHERE id = :task_id
                    AND status = 'pending'
                    AND sandbox_id IS NULL
                    RETURNING id
                """),
                {"task_id": str(task.id), "score": task.score}
            )
            claimed_row = claim_result.fetchone()
            await session.commit()

            if not claimed_row:
                logger.debug(f"Task {task.id} was claimed by another process, skipping")
                return None

            await session.refresh(task)
            return task

    async def assign_task_async(self, task_id: str, agent_id: str) -> None:
        """
        Async version: Assign a task to an agent.

        Args:
            task_id: UUID of the task
            agent_id: UUID of the agent
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(Task).filter(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if task:
                if task.status not in ("pending", "claiming"):
                    logger.warning(
                        f"Task {task_id} has unexpected status {task.status} during assignment"
                    )
                task.assigned_agent_id = agent_id
                task.status = "assigned"
                await session.commit()
                await session.refresh(task)

                # Publish assignment event
                self._publish_event("TASK_ASSIGNED", task, {"agent_id": agent_id})

    async def update_task_status_async(
        self,
        task_id: str,
        status: str,
        result: dict | None = None,
        error_message: str | None = None,
        conversation_id: str | None = None,
        persistence_dir: str | None = None,
    ) -> None:
        """
        Async version: Update task status and result.

        Args:
            task_id: UUID of the task
            status: New status (running, completed, failed)
            result: Optional task result dictionary
            error_message: Optional error message if failed
            conversation_id: Optional OpenHands conversation ID
            persistence_dir: Optional OpenHands conversation persistence directory
        """
        from omoi_os.utils.datetime import utc_now

        async with self.db.get_async_session() as session:
            query_result = await session.execute(
                select(Task).filter(Task.id == task_id)
            )
            task = query_result.scalar_one_or_none()

            if task:
                old_status = task.status
                task.status = status
                if result:
                    task.result = result
                if error_message:
                    task.error_message = error_message
                if conversation_id:
                    task.conversation_id = conversation_id
                if persistence_dir:
                    task.persistence_dir = persistence_dir
                if status == "running" and not task.started_at:
                    task.started_at = utc_now()
                elif status in ("completed", "failed") and not task.completed_at:
                    task.completed_at = utc_now()

                await session.commit()
                await session.refresh(task)

                # Publish status change event
                event_type = {
                    "running": "TASK_STARTED",
                    "completed": "TASK_COMPLETED",
                    "failed": "TASK_FAILED",
                    "cancelled": "TASK_CANCELLED",
                }.get(status, "TASK_STATUS_CHANGED")

                self._publish_event(
                    event_type,
                    task,
                    {
                        "old_status": old_status,
                        "error_message": error_message,
                        "has_result": result is not None,
                    },
                )

    async def get_timed_out_tasks_async(self) -> list[Task]:
        """
        Async version: Get all tasks that have exceeded their timeout.

        Returns:
            List of timed-out Task objects
        """
        from omoi_os.utils.datetime import utc_now

        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(Task).filter(
                    Task.status == "running",
                    Task.timeout_seconds.isnot(None),
                )
            )
            tasks = result.scalars().all()

            timed_out_tasks = []
            now = utc_now()
            for task in tasks:
                if task.started_at:
                    elapsed_seconds = (now - task.started_at).total_seconds()
                    if elapsed_seconds > task.timeout_seconds:
                        timed_out_tasks.append(task)

            return timed_out_tasks

    async def mark_task_timeout_async(
        self, task_id: str, reason: str = "timeout_exceeded"
    ) -> bool:
        """
        Async version: Mark a task as failed due to timeout.

        Args:
            task_id: UUID of the task to mark as timed out
            reason: Timeout reason

        Returns:
            True if task was marked as timed out, False if task not found
        """
        from omoi_os.utils.datetime import utc_now

        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(Task).filter(Task.id == task_id)
            )
            task = result.scalar_one_or_none()

            if not task:
                return False

            if task.status != "running":
                return False

            # Calculate elapsed time for debugging
            elapsed_seconds = 0
            now = utc_now()
            if task.started_at:
                elapsed_seconds = (now - task.started_at).total_seconds()

            task.status = "failed"
            task.error_message = (
                f"Task timed out after {elapsed_seconds:.1f}s: {reason}"
            )
            task.completed_at = now

            await session.commit()
            return True

    async def get_assigned_tasks_async(
        self, agent_id: str, sandbox_id: Optional[str] = None
    ) -> list[Task]:
        """
        Async version: Get all tasks assigned to a specific agent or sandbox.

        Args:
            agent_id: UUID of the agent
            sandbox_id: Optional sandbox ID for sandbox mode queries

        Returns:
            List of Task objects assigned to the agent or sandbox
        """
        async with self.db.get_async_session() as session:
            if sandbox_id:
                stmt = select(Task).filter(
                    Task.sandbox_id == sandbox_id,
                    Task.status.in_(["assigned", "running"]),
                )
            else:
                stmt = select(Task).filter(
                    Task.assigned_agent_id == agent_id,
                    Task.status.in_(["assigned", "running"]),
                )

            result = await session.execute(stmt)
            return list(result.scalars().all())

    # =========================================================================
    # CONCURRENCY CONTROL METHODS
    # =========================================================================
    # These methods help enforce concurrency limits per project to prevent
    # spawning too many sandboxes at once.

    def get_running_count_by_project(self, project_id: str) -> int:
        """
        Get the count of currently running tasks for a project.

        Running tasks include those in 'claiming', 'assigned', or 'running' status.
        This is used to enforce concurrency limits per project.

        Args:
            project_id: UUID of the project

        Returns:
            Count of running tasks for the project
        """
        from omoi_os.models.ticket import Ticket

        with self.db.get_session() as session:
            # Join tasks with tickets to filter by project
            count = (
                session.query(Task)
                .join(Ticket, Task.ticket_id == Ticket.id)
                .filter(
                    Ticket.project_id == project_id,
                    Task.status.in_(["claiming", "assigned", "running"]),
                )
                .count()
            )
            return count

    async def get_running_count_by_project_async(self, project_id: str) -> int:
        """
        Async version: Get the count of currently running tasks for a project.

        Args:
            project_id: UUID of the project

        Returns:
            Count of running tasks for the project
        """
        from sqlalchemy import func
        from omoi_os.models.ticket import Ticket

        async with self.db.get_async_session() as session:
            stmt = (
                select(func.count(Task.id))
                .join(Ticket, Task.ticket_id == Ticket.id)
                .filter(
                    Ticket.project_id == project_id,
                    Task.status.in_(["claiming", "assigned", "running"]),
                )
            )
            result = await session.execute(stmt)
            return result.scalar() or 0

    def get_project_for_task(self, task_id: str) -> Optional[str]:
        """
        Get the project ID for a task (via its ticket).

        Args:
            task_id: UUID of the task

        Returns:
            Project ID if found, None otherwise
        """
        from omoi_os.models.ticket import Ticket

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None

            ticket = session.query(Ticket).filter(Ticket.id == task.ticket_id).first()
            if not ticket:
                return None

            return ticket.project_id

    def get_running_count_by_organization(self, organization_id: str, session=None) -> int:
        """
        Get the count of currently running tasks for an organization.

        Running tasks include those in 'claiming', 'assigned', 'running', or 'validating' status.
        This is used to enforce organization-level agent limits from subscriptions.

        Args:
            organization_id: UUID of the organization
            session: Optional existing session to use

        Returns:
            Count of running tasks for the organization
        """
        from omoi_os.models.ticket import Ticket
        from omoi_os.models.project import Project

        def _count(sess):
            # Join tasks -> tickets -> projects to filter by organization
            count = (
                sess.query(Task)
                .join(Ticket, Task.ticket_id == Ticket.id)
                .join(Project, Ticket.project_id == Project.id)
                .filter(
                    Project.organization_id == organization_id,
                    Task.status.in_(["claiming", "assigned", "running", "validating"]),
                )
                .count()
            )
            return count

        if session:
            return _count(session)
        else:
            with self.db.get_session() as sess:
                return _count(sess)

    def get_agent_limit_for_organization(self, organization_id: str, session=None) -> int:
        """
        Get the agent limit for an organization from their subscription.

        Args:
            organization_id: UUID of the organization
            session: Optional existing session to use

        Returns:
            Agent limit (-1 for unlimited, defaults to 1 if no subscription)
        """
        from omoi_os.models.subscription import (
            Subscription,
            SubscriptionStatus,
            SubscriptionTier,
            TIER_LIMITS,
        )

        def _get_limit(sess):
            # Get active subscription for organization
            result = sess.execute(
                select(Subscription).where(
                    Subscription.organization_id == organization_id,
                    Subscription.status.in_([
                        SubscriptionStatus.ACTIVE.value,
                        SubscriptionStatus.TRIALING.value,
                    ]),
                ).order_by(Subscription.created_at.desc()).limit(1)
            )
            subscription = result.scalar_one_or_none()

            if subscription:
                return subscription.agents_limit

            # No subscription - use FREE tier default
            return TIER_LIMITS[SubscriptionTier.FREE]["agents_limit"]

        if session:
            return _get_limit(session)
        else:
            with self.db.get_session() as sess:
                return _get_limit(sess)

    def can_spawn_agent_for_organization(self, organization_id: str, session=None) -> tuple[bool, str]:
        """
        Check if an organization can spawn another agent based on their subscription limits.

        Args:
            organization_id: UUID of the organization
            session: Optional existing session to use

        Returns:
            Tuple of (can_spawn, reason)
        """
        def _check(sess):
            agent_limit = self.get_agent_limit_for_organization(organization_id, sess)

            # -1 means unlimited
            if agent_limit == -1:
                return True, "unlimited"

            running_count = self.get_running_count_by_organization(organization_id, sess)

            if running_count >= agent_limit:
                return False, f"Organization at agent capacity ({running_count}/{agent_limit})"

            return True, "allowed"

        if session:
            return _check(session)
        else:
            with self.db.get_session() as sess:
                return _check(sess)

    def get_next_task_with_concurrency_limit(
        self,
        max_concurrent_per_project: int = 5,
        phase_id: Optional[str] = None,
        agent_capabilities: Optional[List[str]] = None,
    ) -> Task | None:
        """
        Get highest-scored pending task that respects concurrency limits.

        This method extends get_next_task() by checking:
        1. Project-level concurrency limits (max tasks per project)
        2. Organization-level agent limits (from subscription tier)

        Args:
            max_concurrent_per_project: Maximum concurrent tasks per project (default: 5)
            phase_id: Phase identifier to filter by (None = any phase)
            agent_capabilities: Optional list of agent capabilities for matching

        Returns:
            Task object or None if no eligible tasks available
        """
        from omoi_os.models.ticket import Ticket
        from omoi_os.models.project import Project

        with self.db.get_session() as session:
            # Get pending tasks without sandbox
            query = session.query(Task).filter(
                Task.status == "pending",
                Task.sandbox_id.is_(None),
            )
            if phase_id is not None:
                query = query.filter(Task.phase_id == phase_id)
            tasks = query.all()

            if not tasks:
                return None

            # Filter out tasks with incomplete dependencies, capability mismatches,
            # AND tasks whose projects/organizations have hit concurrency limits
            available_tasks = []
            project_running_counts: dict[str, int] = {}
            org_running_counts: dict[str, int] = {}
            org_agent_limits: dict[str, int] = {}

            for task in tasks:
                if not self._check_dependencies_complete(session, task):
                    continue

                if agent_capabilities is not None and not self._check_capability_match(
                    task, agent_capabilities
                ):
                    continue

                # Get project and organization for this task
                ticket = session.query(Ticket).filter(Ticket.id == task.ticket_id).first()
                if not ticket or not ticket.project_id:
                    # Tasks without a project are allowed (no limit)
                    task.score = self.scorer.compute_score(task)
                    available_tasks.append(task)
                    continue

                project_id = ticket.project_id

                # Get project to find organization
                project = session.query(Project).filter(Project.id == project_id).first()
                organization_id = str(project.organization_id) if project and project.organization_id else None

                # Check organization-level agent limits first (if org exists)
                if organization_id:
                    # Cache org agent limit
                    if organization_id not in org_agent_limits:
                        org_agent_limits[organization_id] = self.get_agent_limit_for_organization(
                            organization_id, session
                        )

                    # Cache org running count
                    if organization_id not in org_running_counts:
                        org_running_counts[organization_id] = self.get_running_count_by_organization(
                            organization_id, session
                        )

                    # Check org limit (-1 means unlimited)
                    org_limit = org_agent_limits[organization_id]
                    if org_limit != -1 and org_running_counts[organization_id] >= org_limit:
                        logger.debug(
                            f"Organization {organization_id} at agent capacity "
                            f"({org_running_counts[organization_id]}/{org_limit}), "
                            f"skipping task {task.id}"
                        )
                        continue

                # Check/cache running count for this project
                if project_id not in project_running_counts:
                    count = (
                        session.query(Task)
                        .join(Ticket, Task.ticket_id == Ticket.id)
                        .filter(
                            Ticket.project_id == project_id,
                            Task.status.in_(["claiming", "assigned", "running"]),
                        )
                        .count()
                    )
                    project_running_counts[project_id] = count

                # Skip if project is at capacity
                if project_running_counts[project_id] >= max_concurrent_per_project:
                    logger.debug(
                        f"Project {project_id} at capacity ({project_running_counts[project_id]}/{max_concurrent_per_project}), "
                        f"skipping task {task.id}"
                    )
                    continue

                # Compute score and add to available tasks
                task.score = self.scorer.compute_score(task)
                available_tasks.append(task)

            if not available_tasks:
                return None

            # Sort by score descending
            task = max(available_tasks, key=lambda t: t.score)

            # Atomic claim using raw SQL
            result = session.execute(
                text("""
                    UPDATE tasks
                    SET status = 'claiming', score = :score
                    WHERE id = :task_id
                    AND status = 'pending'
                    AND sandbox_id IS NULL
                    RETURNING id
                """),
                {"task_id": str(task.id), "score": task.score}
            )
            claimed_row = result.fetchone()
            session.commit()

            if not claimed_row:
                logger.debug(f"Task {task.id} was claimed by another process, skipping")
                return None

            session.refresh(task)
            session.expunge(task)
            return task

    def get_next_validation_task(
        self,
        max_concurrent_per_project: int = 5,
    ) -> Task | None:
        """
        Get next task that needs validation (status = 'pending_validation').

        This method is used by the orchestrator to spawn validation sandboxes
        for tasks that have completed implementation and need review.

        Respects both project-level and organization-level concurrency limits.

        Args:
            max_concurrent_per_project: Maximum concurrent tasks per project (default: 5)

        Returns:
            Task object or None if no tasks need validation
        """
        from omoi_os.models.ticket import Ticket
        from omoi_os.models.project import Project

        with self.db.get_session() as session:
            # Get pending_validation tasks
            query = session.query(Task).filter(
                Task.status == "pending_validation",
            )
            tasks = query.all()

            if not tasks:
                return None

            # Filter by project and organization concurrency limits
            available_tasks = []
            project_running_counts: dict[str, int] = {}
            org_running_counts: dict[str, int] = {}
            org_agent_limits: dict[str, int] = {}

            for task in tasks:
                # Get project ID for this task
                ticket = session.query(Ticket).filter(Ticket.id == task.ticket_id).first()
                if not ticket or not ticket.project_id:
                    # Tasks without a project are allowed (no limit)
                    available_tasks.append(task)
                    continue

                project_id = ticket.project_id

                # Get project to find organization
                project = session.query(Project).filter(Project.id == project_id).first()
                organization_id = str(project.organization_id) if project and project.organization_id else None

                # Check organization-level agent limits first (if org exists)
                if organization_id:
                    # Cache org agent limit
                    if organization_id not in org_agent_limits:
                        org_agent_limits[organization_id] = self.get_agent_limit_for_organization(
                            organization_id, session
                        )

                    # Cache org running count
                    if organization_id not in org_running_counts:
                        org_running_counts[organization_id] = self.get_running_count_by_organization(
                            organization_id, session
                        )

                    # Check org limit (-1 means unlimited)
                    org_limit = org_agent_limits[organization_id]
                    if org_limit != -1 and org_running_counts[organization_id] >= org_limit:
                        logger.debug(
                            f"Organization {organization_id} at agent capacity "
                            f"({org_running_counts[organization_id]}/{org_limit}), "
                            f"skipping validation task {task.id}"
                        )
                        continue

                # Check/cache running count for this project
                if project_id not in project_running_counts:
                    count = (
                        session.query(Task)
                        .join(Ticket, Task.ticket_id == Ticket.id)
                        .filter(
                            Ticket.project_id == project_id,
                            Task.status.in_(["claiming", "assigned", "running", "validating"]),
                        )
                        .count()
                    )
                    project_running_counts[project_id] = count

                # Skip if project is at capacity
                if project_running_counts[project_id] >= max_concurrent_per_project:
                    logger.debug(
                        f"Project {project_id} at capacity ({project_running_counts[project_id]}/{max_concurrent_per_project}), "
                        f"skipping validation task {task.id}"
                    )
                    continue

                available_tasks.append(task)

            if not available_tasks:
                return None

            # Get oldest pending_validation task (FIFO for validation)
            task = min(available_tasks, key=lambda t: t.updated_at or t.created_at)

            # Atomic claim: set status to 'validating'
            result = session.execute(
                text("""
                    UPDATE tasks
                    SET status = 'validating'
                    WHERE id = :task_id
                    AND status = 'pending_validation'
                    RETURNING id
                """),
                {"task_id": str(task.id)}
            )
            claimed_row = result.fetchone()
            session.commit()

            if not claimed_row:
                logger.debug(f"Validation task {task.id} was claimed by another process, skipping")
                return None

            session.refresh(task)
            session.expunge(task)
            return task
