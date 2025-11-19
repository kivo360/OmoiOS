"""Task queue service for managing task assignment and retrieval."""

from typing import List, Optional

from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_scorer import TaskScorer


class TaskQueueService:
    """Manages task queue operations: enqueue, retrieve, assign, update."""

    def __init__(self, db: DatabaseService):
        """
        Initialize task queue service.

        Args:
            db: DatabaseService instance
        """
        self.db = db
        self.scorer = TaskScorer(db)

    def enqueue_task(
        self,
        ticket_id: str,
        phase_id: str,
        task_type: str,
        description: str,
        priority: str,
        dependencies: dict | None = None,
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

        Returns:
            Created Task object
        """
        with self.db.get_session() as session:
            task = Task(
                ticket_id=ticket_id,
                phase_id=phase_id,
                task_type=task_type,
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
            return task

    def get_next_task(
        self, phase_id: str, agent_capabilities: Optional[List[str]] = None
    ) -> Task | None:
        """
        Get highest-scored pending task for a phase that has all dependencies completed.
        Uses dynamic scoring per REQ-TQM-PRI-002.
        Verifies capability matching per REQ-TQM-ASSIGN-001.

        Args:
            phase_id: Phase identifier to filter by
            agent_capabilities: Optional list of agent capabilities for matching (REQ-TQM-ASSIGN-001)

        Returns:
            Task object or None if no pending tasks with completed dependencies and matching capabilities
        """
        with self.db.get_session() as session:
            tasks = (
                session.query(Task)
                .filter(Task.status == "pending", Task.phase_id == phase_id)
                .all()
            )
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

            # Update score in database
            session.query(Task).filter(Task.id == task.id).update({"score": task.score})
            session.commit()
            session.refresh(task)  # Refresh to ensure all attributes are loaded

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

        Args:
            task_id: UUID of the task
            agent_id: UUID of the agent
        """
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.assigned_agent_id = agent_id
                task.status = "assigned"

    def update_task_status(
        self,
        task_id: str,
        status: str,
        result: dict | None = None,
        error_message: str | None = None,
        conversation_id: str | None = None,
    ) -> None:
        """
        Update task status and result.

        Args:
            task_id: UUID of the task
            status: New status (running, completed, failed)
            result: Optional task result dictionary
            error_message: Optional error message if failed
            conversation_id: Optional OpenHands conversation ID
        """
        from omoi_os.utils.datetime import utc_now

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = status
                if result:
                    task.result = result
                if error_message:
                    task.error_message = error_message
                if conversation_id:
                    task.conversation_id = conversation_id
                if status == "running" and not task.started_at:
                    task.started_at = utc_now()
                elif status in ("completed", "failed") and not task.completed_at:
                    task.completed_at = utc_now()

    def get_assigned_tasks(self, agent_id: str) -> list[Task]:
        """
        Get all tasks assigned to a specific agent.

        Args:
            agent_id: UUID of the agent

        Returns:
            List of Task objects assigned to the agent
        """
        with self.db.get_session() as session:
            tasks = (
                session.query(Task)
                .filter(
                    Task.assigned_agent_id == agent_id,
                    Task.status.in_(["assigned", "running"]),
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
            import logging

            logger = logging.getLogger(__name__)
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
            task.assigned_agent_id = (
                None  # Clear assignment so it can be picked up again
            )

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

    def get_cancellable_tasks(self, agent_id: str | None = None) -> list[Task]:
        """
        Get all tasks that can be cancelled.

        Args:
            agent_id: Optional agent ID to filter by

        Returns:
            List of cancellable Task objects
        """
        with self.db.get_session() as session:
            query = session.query(Task).filter(Task.status.in_(["assigned", "running"]))

            if agent_id:
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
