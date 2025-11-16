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
            # Expunge the task so it can be used outside the session
            session.expunge(task)
            return task

    def get_next_task(self, phase_id: str) -> Task | None:
        """
        Get highest priority pending task for a phase that has all dependencies completed.

        Args:
            phase_id: Phase identifier to filter by

        Returns:
            Task object or None if no pending tasks with completed dependencies
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
            
            # Filter out tasks with incomplete dependencies
            available_tasks = []
            for task in tasks:
                if self._check_dependencies_complete(session, task):
                    available_tasks.append(task)
            
            if not available_tasks:
                return None
            
            # Sort by priority descending
            task = max(available_tasks, key=lambda t: priority_order.get(t.priority, 0))
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
        dependency_tasks = (
            session.query(Task)
            .filter(Task.id.in_(depends_on))
            .all()
        )
        
        # If we can't find all dependencies, consider them incomplete
        if len(dependency_tasks) != len(depends_on):
            return False
        
        # All dependencies must be completed
        return all(dep_task.status == "completed" for dep_task in dependency_tasks)

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

    def detect_circular_dependencies(self, task_id: str, depends_on: list[str], visited: list[str] | None = None) -> list[str] | None:
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
                    cycle = self.detect_circular_dependencies(dep_id, dep_depends_on, visited.copy())
                    if cycle:
                        return cycle
        
        return None
