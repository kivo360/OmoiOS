"""Scheduler service for DAG-based task batching and parallel execution."""

from collections import defaultdict, deque
from typing import Optional

from omoi_os.models.task import Task
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.resource_lock import ResourceLockService
from omoi_os.services.task_queue import TaskQueueService


class SchedulerService:
    """Schedules tasks for parallel execution using DAG evaluation."""

    def __init__(
        self,
        db: DatabaseService,
        task_queue: TaskQueueService,
        registry: AgentRegistryService,
        lock_service: ResourceLockService,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize scheduler service.

        Args:
            db: DatabaseService instance
            task_queue: TaskQueueService instance
            registry: AgentRegistryService instance
            lock_service: ResourceLockService instance
            event_bus: Optional EventBusService for telemetry
        """
        self.db = db
        self.task_queue = task_queue
        self.registry = registry
        self.lock_service = lock_service
        self.event_bus = event_bus

    def get_ready_tasks(
        self,
        phase_id: Optional[str] = None,
        limit: Optional[int] = None,
        required_capabilities: Optional[list[str]] = None,
    ) -> list[Task]:
        """
        Get batch of ready tasks using DAG evaluation.

        A task is "ready" if:
        1. Status is "pending"
        2. All dependencies are completed
        3. Required resources are not locked (if applicable)

        Args:
            phase_id: Optional phase ID to filter by
            limit: Maximum number of tasks to return
            required_capabilities: Optional capabilities required for task execution

        Returns:
            List of ready Task objects, sorted by priority
        """
        with self.db.get_session() as session:
            # Get all pending tasks
            query = session.query(Task).filter(Task.status == "pending")
            if phase_id:
                query = query.filter(Task.phase_id == phase_id)

            all_tasks = query.all()

            # Build dependency graph
            task_map = {task.id: task for task in all_tasks}
            dependency_graph = defaultdict(list)
            in_degree = defaultdict(int)

            for task in all_tasks:
                in_degree[task.id] = 0
                if task.dependencies:
                    depends_on = task.dependencies.get("depends_on", [])
                    for dep_id in depends_on:
                        if dep_id in task_map:
                            dependency_graph[dep_id].append(task.id)
                            in_degree[task.id] += 1

            # Find ready tasks (in-degree == 0 and dependencies completed)
            ready_tasks = []
            for task in all_tasks:
                if in_degree[task.id] == 0:
                    # Check if all dependencies are actually completed
                    if self._check_dependencies_complete(session, task):
                        ready_tasks.append(task)

            # Sort by priority
            priority_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
            ready_tasks.sort(key=lambda t: priority_order.get(t.priority, 0), reverse=True)

            # Filter by capabilities if specified
            if required_capabilities:
                filtered_tasks = []
                for task in ready_tasks:
                    # Check if any agent can handle this task
                    match = self.registry.find_best_agent(
                        required_capabilities=required_capabilities,
                        phase_id=task.phase_id,
                        agent_type="worker",
                    )
                    if match:
                        filtered_tasks.append(task)
                ready_tasks = filtered_tasks

            # Apply limit
            if limit:
                ready_tasks = ready_tasks[:limit]

            # Expunge tasks so they can be used outside the session
            for task in ready_tasks:
                session.expunge(task)

            # Emit telemetry
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="scheduler.ready_tasks",
                        entity_type="scheduler",
                        entity_id="default",
                        payload={
                            "ready_count": len(ready_tasks),
                            "phase_id": phase_id,
                            "task_ids": [t.id for t in ready_tasks],
                        },
                    )
                )

            return ready_tasks

    def _check_dependencies_complete(self, session, task: Task) -> bool:
        """Check if all dependencies for a task are completed."""
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

    def assign_tasks_to_agents(
        self,
        tasks: list[Task],
        max_assignments: Optional[int] = None,
    ) -> dict[str, Optional[str]]:
        """
        Assign tasks to best-fit agents based on capabilities.

        Args:
            tasks: List of tasks to assign
            max_assignments: Maximum number of assignments to make (None = all)

        Returns:
            Dictionary mapping task_id -> agent_id (or None if no suitable agent found)
        """
        assignments = {}
        assignments_made = 0

        for task in tasks:
            if max_assignments and assignments_made >= max_assignments:
                break

            # Find best agent for this task
            # Extract required capabilities from task metadata if available
            required_capabilities = []
            if task.dependencies:
                # Could extract from task metadata in future
                pass

            match = self.registry.find_best_agent(
                required_capabilities=required_capabilities if required_capabilities else None,
                phase_id=task.phase_id,
                agent_type="worker",
            )

            if match:
                agent = match["agent"]
                # Check agent capacity
                # For now, we'll assign if agent is idle
                # In future, track concurrent task count per agent
                if agent.status == "idle":
                    assignments[task.id] = agent.id
                    assignments_made += 1
                else:
                    assignments[task.id] = None
            else:
                assignments[task.id] = None

        return assignments

    def schedule_and_assign(
        self,
        phase_id: Optional[str] = None,
        limit: Optional[int] = None,
        required_capabilities: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Get ready tasks and assign them to agents in one operation.

        Args:
            phase_id: Optional phase ID to filter by
            limit: Maximum number of tasks to schedule
            required_capabilities: Optional capabilities required

        Returns:
            List of assignment dictionaries with task_id, agent_id, and task info
        """
        # Get ready tasks
        ready_tasks = self.get_ready_tasks(
            phase_id=phase_id,
            limit=limit,
            required_capabilities=required_capabilities,
        )

        if not ready_tasks:
            return []

        # Assign to agents
        assignments = self.assign_tasks_to_agents(ready_tasks, max_assignments=limit)

        # Create assignment results
        results = []
        for task in ready_tasks:
            agent_id = assignments.get(task.id)
            results.append(
                {
                    "task_id": task.id,
                    "agent_id": agent_id,
                    "task": task,
                    "assigned": agent_id is not None,
                }
            )

        return results
