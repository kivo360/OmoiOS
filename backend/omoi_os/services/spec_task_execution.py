"""Service for executing SpecTasks via the sandbox system.

This service bridges the gap between spec-driven development (SpecTasks)
and the execution system (Tasks + TaskQueueService + Daytona sandboxes).

Flow:
1. User approves a Spec for execution (design_approved=True)
2. This service converts SpecTasks → Tasks via a bridging Ticket
3. TaskQueueService picks up Tasks and OrchestratorWorker spawns sandboxes
4. On Task completion, we update the SpecTask status

Architecture Notes:
- SpecTask (omoi_os/models/spec.py) - spec-driven tasks linked to Spec
- Task (omoi_os/models/task.py) - execution tasks linked to Ticket
- The sandbox system (DaytonaSpawner) only knows about Tasks, not SpecTasks
"""

from dataclasses import dataclass, field
from functools import lru_cache
import re
from typing import Optional, List, Dict, TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from omoi_os.logging import get_logger
from omoi_os.models.spec import Spec, SpecTask
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.task_queue import TaskQueueService

if TYPE_CHECKING:
    from omoi_os.services.coordination import CoordinationService

logger = get_logger(__name__)


@dataclass
class ExecutionStats:
    """Statistics from SpecTask execution conversion."""

    tasks_created: int = 0
    tasks_skipped: int = 0
    ticket_id: Optional[str] = None
    parallel_groups_created: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "tasks_created": self.tasks_created,
            "tasks_skipped": self.tasks_skipped,
            "ticket_id": self.ticket_id,
            "parallel_groups_created": self.parallel_groups_created,
            "errors": self.errors,
        }


@dataclass
class ExecutionResult:
    """Result of SpecTask execution initiation."""

    success: bool
    message: str
    stats: ExecutionStats = field(default_factory=ExecutionStats)


@dataclass
class ParallelGroup:
    """A group of tasks that can run in parallel with a continuation.

    Parsed from spec.phase_data["sync"]["dependency_analysis"]["parallel_opportunities"].
    """

    source_task_ids: List[str]  # Tasks that can run in parallel
    continuation_task_id: Optional[str]  # Task that depends on all sources
    description: str  # Original description from sync phase
    merge_strategy: str = "combine"  # How to merge results


class SpecTaskExecutionService:
    """Service for converting and executing SpecTasks via sandbox system.

    This service:
    1. Creates a bridging Ticket for a Spec (if not exists)
    2. Converts pending SpecTasks to executable Tasks
    3. Tasks are then picked up by TaskQueueService and executed via Daytona
    4. Listens for Task completion events to update SpecTask status
    """

    # Map SpecTask priority to Task priority
    PRIORITY_MAP = {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
    }

    # Map SpecTask phase to Task phase_id
    # NOTE: By default, all phases map to PHASE_IMPLEMENTATION to ensure:
    # 1. Tasks run in continuous mode (auto-enabled for implementation/validation)
    # 2. Tasks run to completion instead of stopping early
    # The original phase mapping is preserved in ORIGINAL_PHASE_MAP for reference.
    PHASE_MAP = {
        "Requirements": "PHASE_IMPLEMENTATION",  # Changed from PHASE_INITIAL
        "Design": "PHASE_IMPLEMENTATION",         # Changed from PHASE_INITIAL
        "Implementation": "PHASE_IMPLEMENTATION",
        "Testing": "PHASE_INTEGRATION",
        "Done": "PHASE_REFACTORING",
    }

    # Original phase mapping preserved for reference (not used by default)
    # Set force_implementation_phase=False in execute_spec_tasks() to use this
    ORIGINAL_PHASE_MAP = {
        "Requirements": "PHASE_INITIAL",
        "Design": "PHASE_INITIAL",
        "Implementation": "PHASE_IMPLEMENTATION",
        "Testing": "PHASE_INTEGRATION",
        "Done": "PHASE_REFACTORING",
    }

    def __init__(
        self,
        db: DatabaseService,
        task_queue: Optional[TaskQueueService] = None,
        event_bus: Optional[EventBusService] = None,
        coordination: Optional["CoordinationService"] = None,
    ):
        """Initialize the service.

        Args:
            db: Database service for persistence
            task_queue: Optional task queue service (creates one if not provided)
            event_bus: Optional event bus for completion notifications
            coordination: Optional coordination service for parallel task joins.
                         When provided, parallel opportunities from spec.phase_data
                         will trigger join_tasks() calls for synthesis.
        """
        self.db = db
        self.task_queue = task_queue
        self.event_bus = event_bus
        self.coordination = coordination
        self._completion_subscribed = False

    def subscribe_to_completions(self) -> None:
        """Subscribe to task completion events to update SpecTask status."""
        if self._completion_subscribed or not self.event_bus:
            return

        self.event_bus.subscribe("TASK_COMPLETED", self._handle_task_completed)
        self.event_bus.subscribe("TASK_FAILED", self._handle_task_failed)
        self._completion_subscribed = True
        logger.info("subscribed_to_task_completions")

    def _handle_task_completed(self, event_data: dict) -> None:
        """Handle task completion events to update SpecTask."""
        task_id = event_data.get("entity_id")
        if not task_id:
            return

        # Check if this task has a linked spec_task_id
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task or not task.result:
                return

            spec_task_id = task.result.get("spec_task_id")
            if not spec_task_id:
                return

            # Update the SpecTask status
            spec_task = session.get(SpecTask, spec_task_id)
            if spec_task:
                spec_task.status = "completed"
                session.commit()
                logger.info(
                    "spec_task_completed",
                    spec_task_id=spec_task_id,
                    task_id=task_id,
                )

    def _handle_task_failed(self, event_data: dict) -> None:
        """Handle task failure events to update SpecTask."""
        task_id = event_data.get("entity_id")
        if not task_id:
            return

        # Check if this task has a linked spec_task_id
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task or not task.result:
                return

            spec_task_id = task.result.get("spec_task_id")
            if not spec_task_id:
                return

            # Update the SpecTask status
            spec_task = session.get(SpecTask, spec_task_id)
            if spec_task:
                spec_task.status = "blocked"  # Mark as blocked on failure
                session.commit()
                logger.info(
                    "spec_task_blocked_on_failure",
                    spec_task_id=spec_task_id,
                    task_id=task_id,
                )

    async def execute_spec_tasks(
        self,
        spec_id: str,
        task_ids: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """Execute SpecTasks by converting them to Tasks and enqueuing.

        This is the main entry point for executing spec tasks. It:
        1. Gets or creates a bridging Ticket for the Spec
        2. Converts pending SpecTasks to executable Tasks
        3. Enqueues Tasks for sandbox execution

        Args:
            spec_id: ID of the spec whose tasks to execute
            task_ids: Optional list of specific SpecTask IDs to execute.
                     If None, executes all pending tasks.

        Returns:
            ExecutionResult with success status and statistics
        """
        stats = ExecutionStats()

        async with self.db.get_async_session() as session:
            # Get spec with tasks
            result = await session.execute(
                select(Spec)
                .filter(Spec.id == spec_id)
                .options(selectinload(Spec.tasks))
            )
            spec = result.scalar_one_or_none()

            if not spec:
                return ExecutionResult(
                    success=False,
                    message=f"Spec not found: {spec_id}",
                    stats=stats,
                )

            # Check if design is approved (required for execution)
            if not spec.design_approved:
                return ExecutionResult(
                    success=False,
                    message="Spec design must be approved before executing tasks",
                    stats=stats,
                )

            # Get or create bridging ticket
            ticket_id = await self._get_or_create_ticket(session, spec)
            stats.ticket_id = ticket_id

            # Filter tasks to execute
            tasks_to_execute = []
            for spec_task in spec.tasks:
                # Skip if specific IDs provided and not in list
                if task_ids and spec_task.id not in task_ids:
                    continue

                # Only execute pending tasks
                if spec_task.status != "pending":
                    stats.tasks_skipped += 1
                    continue

                tasks_to_execute.append(spec_task)

            if not tasks_to_execute:
                return ExecutionResult(
                    success=True,
                    message="No pending tasks to execute",
                    stats=stats,
                )

            # Build mapping from spec_task_id to created task_id for parallel coordination
            task_mapping: Dict[str, str] = {}

            # Convert and enqueue each task
            for spec_task in tasks_to_execute:
                try:
                    task = await self._convert_and_enqueue(
                        session, spec, spec_task, ticket_id
                    )
                    if task:
                        # Mark SpecTask as in_progress
                        spec_task.status = "in_progress"
                        spec_task.assigned_agent = f"task:{task.id}"
                        stats.tasks_created += 1
                        # Track mapping for parallel coordination
                        task_mapping[spec_task.id] = task.id
                except Exception as e:
                    error_msg = f"Failed to convert task {spec_task.id}: {e}"
                    stats.errors.append(error_msg)
                    logger.error(
                        "spec_task_conversion_failed",
                        spec_task_id=spec_task.id,
                        error=str(e),
                    )

            await session.commit()

            # Register parallel task coordination (join points) for synthesis
            # This wires CoordinationService.join_tasks() to SynthesisService
            if self.coordination and task_mapping:
                await self._register_parallel_coordination(
                    spec, task_mapping, stats
                )

            # Publish execution started event
            if self.event_bus and stats.tasks_created > 0:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="SPEC_EXECUTION_STARTED",
                        entity_type="spec",
                        entity_id=spec_id,
                        payload={
                            "spec_id": spec_id,
                            "ticket_id": ticket_id,
                            "tasks_created": stats.tasks_created,
                            "parallel_groups_created": stats.parallel_groups_created,
                        },
                    )
                )

            return ExecutionResult(
                success=True,
                message=f"Created {stats.tasks_created} tasks for execution ({stats.parallel_groups_created} parallel groups)",
                stats=stats,
            )

    async def _get_or_create_ticket(self, session, spec: Spec) -> str:
        """Get existing ticket for spec or create a new one.

        Args:
            session: Database session
            spec: The spec to get/create ticket for

        Returns:
            Ticket ID
        """
        # Look for existing ticket with matching spec reference in context
        result = await session.execute(
            select(Ticket)
            .filter(Ticket.project_id == spec.project_id)
            .filter(Ticket.context["spec_id"].astext == spec.id)
        )
        existing_ticket = result.scalar_one_or_none()

        if existing_ticket:
            logger.debug(
                "using_existing_ticket",
                ticket_id=existing_ticket.id,
                spec_id=spec.id,
            )
            return existing_ticket.id

        # Create new bridging ticket - include user_id from spec for ownership
        ticket = Ticket(
            id=str(uuid4()),
            title=f"[Spec] {spec.title}",
            description=spec.description,
            phase_id="PHASE_IMPLEMENTATION",
            status="building",
            priority="MEDIUM",
            project_id=spec.project_id,
            user_id=spec.user_id,  # Inherit user ownership from spec
            context={
                "spec_id": spec.id,
                "spec_title": spec.title,
                "source": "spec_task_execution",
            },
        )
        session.add(ticket)
        await session.flush()  # Get the ID

        logger.info(
            "created_bridging_ticket",
            ticket_id=ticket.id,
            spec_id=spec.id,
            user_id=str(spec.user_id) if spec.user_id else None,
        )

        return ticket.id

    async def _convert_and_enqueue(
        self,
        session,
        spec: Spec,
        spec_task: SpecTask,
        ticket_id: str,
    ) -> Optional[Task]:
        """Convert a SpecTask to Task and enqueue for execution.

        Args:
            session: Database session
            spec: Parent spec
            spec_task: SpecTask to convert
            ticket_id: Bridging ticket ID

        Returns:
            Created Task or None if failed
        """
        # Map priority and phase
        priority = self.PRIORITY_MAP.get(spec_task.priority.lower(), "MEDIUM")
        phase_id = self.PHASE_MAP.get(spec_task.phase, "PHASE_IMPLEMENTATION")

        # Determine task type from phase
        # IMPORTANT: All tasks default to "implement_feature" to ensure:
        # 1. They're analyzed as implementation mode (not exploration)
        # 2. Continuous mode is auto-enabled (only for implementation/validation)
        # 3. Tasks run to completion instead of stopping early
        # The only exception is Testing phase which uses "write_tests"
        task_type = "implement_feature"  # Default - ensures implementation mode
        phase_lower = spec_task.phase.lower()
        if "test" in phase_lower:
            task_type = "write_tests"
        # NOTE: Design and Requirements phases now use "implement_feature" task_type
        # to ensure they run in implementation mode with continuous execution.
        # Previously they used "analyze_requirements" which caused exploration mode.

        # Build description with spec context
        description = (
            f"{spec_task.description or spec_task.title}\n\n"
            f"---\n"
            f"Spec Context:\n"
            f"- Spec Title: {spec.title}\n"
            f"- Spec Phase: {spec.phase}\n"
            f"- Task Phase: {spec_task.phase}\n"
        )

        # Handle dependencies
        dependencies = None
        if spec_task.dependencies:
            dependencies = {"depends_on": spec_task.dependencies}

        # Create the Task
        task = Task(
            id=str(uuid4()),
            ticket_id=ticket_id,
            phase_id=phase_id,
            task_type=task_type,
            title=spec_task.title,
            description=description,
            priority=priority,
            status="pending",
            dependencies=dependencies,
            result={
                "spec_task_id": spec_task.id,  # Link back to SpecTask
                "spec_id": spec.id,
            },
        )

        session.add(task)
        await session.flush()  # Get the ID

        logger.info(
            "converted_spec_task",
            spec_task_id=spec_task.id,
            task_id=task.id,
            task_type=task_type,
            phase_id=phase_id,
        )

        # Publish task created event for orchestrator
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="TASK_CREATED",
                    entity_type="task",
                    entity_id=task.id,
                    payload={
                        "task_id": task.id,
                        "ticket_id": ticket_id,
                        "spec_task_id": spec_task.id,
                        "spec_id": spec.id,
                    },
                )
            )

        return task

    def _parse_parallel_opportunities(
        self,
        spec: Spec,
        task_mapping: Dict[str, str],
    ) -> List[ParallelGroup]:
        """Parse parallel opportunities from spec.phase_data and resolve to task IDs.

        Parallel opportunities are generated during the SYNC phase and stored in:
        spec.phase_data["sync"]["dependency_analysis"]["parallel_opportunities"]

        Format examples:
        - "TSK-003 and TSK-004 can run in parallel after TSK-002"
        - "TSK-006, TSK-007, and TSK-008 are independent and can run concurrently"

        Args:
            spec: The spec containing phase_data with parallel opportunities
            task_mapping: Mapping from spec_task_id to created task_id

        Returns:
            List of ParallelGroup instances with resolved task IDs
        """
        groups = []

        # Get parallel opportunities from phase_data
        sync_data = spec.phase_data.get("sync", {}) if spec.phase_data else {}
        dependency_analysis = sync_data.get("dependency_analysis", {})
        opportunities = dependency_analysis.get("parallel_opportunities", [])

        if not opportunities:
            logger.debug(
                "no_parallel_opportunities_found",
                spec_id=spec.id,
            )
            return groups

        # Also get the task dependency graph for finding continuation tasks
        task_dep_graph = dependency_analysis.get("task_dependency_graph", {})

        for opp in opportunities:
            try:
                # Extract task IDs from the opportunity description
                # Pattern: "TSK-XXX" where XXX is alphanumeric
                task_pattern = r"(TSK-[A-Za-z0-9-]+)"
                found_ids = re.findall(task_pattern, opp)

                if len(found_ids) < 2:
                    logger.debug(
                        "parallel_opportunity_too_few_tasks",
                        opportunity=opp,
                        found_ids=found_ids,
                    )
                    continue

                # Resolve spec task IDs to created task IDs
                resolved_ids = []
                for spec_task_id in found_ids:
                    if spec_task_id in task_mapping:
                        resolved_ids.append(task_mapping[spec_task_id])
                    else:
                        logger.warning(
                            "parallel_opportunity_task_not_found",
                            spec_task_id=spec_task_id,
                            opportunity=opp,
                        )

                if len(resolved_ids) < 2:
                    logger.debug(
                        "parallel_opportunity_not_enough_resolved",
                        opportunity=opp,
                        resolved_count=len(resolved_ids),
                    )
                    continue

                # Find continuation task (task that depends on ALL the parallel tasks)
                # Look in task_dep_graph for a task that has all resolved IDs as dependencies
                continuation_task_id = self._find_continuation_task(
                    resolved_ids, found_ids, task_dep_graph, task_mapping
                )

                groups.append(
                    ParallelGroup(
                        source_task_ids=resolved_ids,
                        continuation_task_id=continuation_task_id,
                        description=opp,
                        merge_strategy="combine",
                    )
                )

                logger.info(
                    "parallel_group_created",
                    spec_id=spec.id,
                    source_count=len(resolved_ids),
                    has_continuation=continuation_task_id is not None,
                    description=opp[:100],
                )

            except Exception as e:
                logger.warning(
                    "parallel_opportunity_parse_error",
                    opportunity=opp,
                    error=str(e),
                )
                continue

        return groups

    def _find_continuation_task(
        self,
        resolved_source_ids: List[str],
        spec_source_ids: List[str],
        task_dep_graph: Dict[str, List[str]],
        task_mapping: Dict[str, str],
    ) -> Optional[str]:
        """Find the continuation task that depends on all source tasks.

        Looks in the task dependency graph for a task whose dependencies include
        all the source tasks. This task becomes the continuation that receives
        the merged synthesis context.

        Args:
            resolved_source_ids: Task IDs (after mapping)
            spec_source_ids: Original spec task IDs (e.g., TSK-003)
            task_dep_graph: Dependency graph from sync phase
            task_mapping: Mapping from spec_task_id to created task_id

        Returns:
            Task ID of continuation task, or None if not found
        """
        spec_source_set = set(spec_source_ids)

        # Look for a task that depends on ALL source tasks
        for spec_task_id, dependencies in task_dep_graph.items():
            if not dependencies:
                continue

            dep_set = set(dependencies)
            # Check if this task depends on ALL source tasks
            if spec_source_set.issubset(dep_set):
                # This task depends on all parallel sources - it's the continuation
                if spec_task_id in task_mapping:
                    return task_mapping[spec_task_id]

        return None

    async def _register_parallel_coordination(
        self,
        spec: Spec,
        task_mapping: Dict[str, str],
        stats: ExecutionStats,
    ) -> None:
        """Register parallel task groups with CoordinationService for synthesis.

        Parses parallel opportunities from spec.phase_data and calls join_tasks()
        for each group. This publishes coordination.join.created events that
        SynthesisService listens for.

        Args:
            spec: The spec with phase_data containing parallel opportunities
            task_mapping: Mapping from spec_task_id to created task_id
            stats: Stats object to update with parallel_groups_created
        """
        if not self.coordination:
            return

        # Parse parallel opportunities from spec phase_data
        parallel_groups = self._parse_parallel_opportunities(spec, task_mapping)

        if not parallel_groups:
            logger.debug(
                "no_parallel_groups_to_register",
                spec_id=spec.id,
            )
            return

        for group in parallel_groups:
            try:
                # Skip groups without a continuation task
                # Without a continuation, there's nothing to inject synthesis context into
                if not group.continuation_task_id:
                    logger.info(
                        "parallel_group_skipped_no_continuation",
                        spec_id=spec.id,
                        source_count=len(group.source_task_ids),
                        description=group.description[:100],
                    )
                    continue

                # Generate a unique join ID
                join_id = f"join-{spec.id}-{uuid4().hex[:8]}"

                # Register the join with CoordinationService
                # This publishes coordination.join.created event that SynthesisService listens for
                # The continuation task already exists (created by _convert_and_enqueue),
                # so we use register_join() instead of join_tasks()
                self.coordination.register_join(
                    join_id=join_id,
                    source_task_ids=group.source_task_ids,
                    continuation_task_id=group.continuation_task_id,
                    merge_strategy=group.merge_strategy,
                )

                stats.parallel_groups_created += 1

                logger.info(
                    "parallel_coordination_registered",
                    spec_id=spec.id,
                    join_id=join_id,
                    source_count=len(group.source_task_ids),
                    continuation_task_id=group.continuation_task_id,
                    merge_strategy=group.merge_strategy,
                )

            except Exception as e:
                logger.error(
                    "parallel_coordination_registration_failed",
                    spec_id=spec.id,
                    error=str(e),
                    source_count=len(group.source_task_ids),
                )

    async def get_execution_status(self, spec_id: str) -> dict:
        """Get execution status for a spec.

        Args:
            spec_id: Spec ID to get status for

        Returns:
            Status dict with task counts by status
        """
        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(Spec)
                .filter(Spec.id == spec_id)
                .options(selectinload(Spec.tasks))
            )
            spec = result.scalar_one_or_none()

            if not spec:
                return {"error": "Spec not found"}

            status_counts = {
                "pending": 0,
                "in_progress": 0,
                "completed": 0,
                "blocked": 0,
            }

            for task in spec.tasks:
                status = task.status.lower()
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts["pending"] += 1  # Default unknown to pending

            total = sum(status_counts.values())
            completed = status_counts["completed"]

            return {
                "spec_id": spec_id,
                "total_tasks": total,
                "status_counts": status_counts,
                "progress": (completed / total * 100) if total > 0 else 0,
                "is_complete": completed == total and total > 0,
            }


@lru_cache(maxsize=1)
def get_spec_task_execution_service(
    db: Optional[DatabaseService] = None,
    task_queue: Optional[TaskQueueService] = None,
    event_bus: Optional[EventBusService] = None,
    coordination: Optional["CoordinationService"] = None,
) -> SpecTaskExecutionService:
    """Get the SpecTaskExecutionService singleton.

    Note: Due to lru_cache, only the first call's arguments are used.
    For testing, use SpecTaskExecutionService directly.

    Args:
        db: Database service for persistence
        task_queue: Optional task queue service
        event_bus: Optional event bus for completion notifications
        coordination: Optional coordination service for parallel task synthesis.
                     When provided, parallel opportunities from spec.phase_data
                     will trigger join_tasks() calls for synthesis.
    """
    if db is None:
        from omoi_os.services.database import get_db_service
        db = get_db_service()

    return SpecTaskExecutionService(
        db=db,
        task_queue=task_queue,
        event_bus=event_bus,
        coordination=coordination,
    )
