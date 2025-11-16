"""Task queue service for managing task assignment and retrieval."""

from uuid import UUID

from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService


class TaskQueueService:
    """Manages task queue operations: enqueue, retrieve, assign, update."""

    def __init__(self, db: DatabaseService):
        """
        Initialize task queue service.

        Args:
            db: DatabaseService instance
        """
        self.db = db

    def enqueue_task(
        self,
        ticket_id: str,
        phase_id: str,
        task_type: str,
        description: str,
        priority: str,
    ) -> Task:
        """
        Add a task to the queue.

        Args:
            ticket_id: UUID of the parent ticket
            phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")
            task_type: Type of task (e.g., "implement_feature")
            description: Task description
            priority: Task priority (CRITICAL, HIGH, MEDIUM, LOW)

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
            )
            session.add(task)
            session.flush()
            session.refresh(task)
            # Expunge the task so it can be used outside the session
            session.expunge(task)
            return task

    def get_next_task(self, phase_id: str) -> Task | None:
        """
        Get highest priority pending task for a phase.

        Args:
            phase_id: Phase identifier to filter by

        Returns:
            Task object or None if no pending tasks
        """
        with self.db.get_session() as session:
            # Priority order: CRITICAL > HIGH > MEDIUM > LOW
            priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
            tasks = (
                session.query(Task)
                .filter(Task.status == "pending", Task.phase_id == phase_id)
                .all()
            )
            if not tasks:
                return None
            # Sort by priority descending
            task = max(tasks, key=lambda t: priority_order.get(t.priority, 0))
            # Expunge so it can be used outside the session
            session.expunge(task)
            return task

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
                .filter(Task.assigned_agent_id == agent_id, Task.status.in_(["assigned", "running"]))
                .all()
            )
            # Expunge all tasks so they can be used outside the session
            for task in tasks:
                session.expunge(task)
            return tasks
