"""Phase progression service for automatic ticket advancement and task spawning.

This service implements two key hooks:
- Hook 1: Auto-advance ticket when all phase tasks complete
- Hook 2: Auto-spawn next phase tasks when ticket enters new phase

The service subscribes to events and coordinates between:
- TaskQueueService: For checking task completion status
- TicketWorkflowOrchestrator: For advancing tickets between phases
- PhaseGateService: For validating phase gate requirements
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from omoi_os.logging import get_logger
from omoi_os.models.phases import Phase
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.spec_driven_settings import (
    SpecDrivenSettingsService,
    get_spec_driven_settings_service,
)
from omoi_os.services.task_queue import TaskQueueService

if TYPE_CHECKING:
    from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator

logger = get_logger(__name__)


# Phase-to-task-type mapping for auto-spawning tasks
# These define the initial tasks to spawn when entering each phase
PHASE_INITIAL_TASKS: dict[str, list[dict[str, Any]]] = {
    "PHASE_REQUIREMENTS": [
        {
            "task_type": "analyze_requirements",
            "description": "Analyze and document requirements for this ticket",
            "priority": "high",
        }
    ],
    "PHASE_DESIGN": [
        {
            "task_type": "create_design",
            "description": "Create design documentation and technical approach",
            "priority": "high",
        }
    ],
    "PHASE_IMPLEMENTATION": [
        {
            "task_type": "implement_feature",
            "description": "Implement the feature according to design specifications",
            "priority": "high",
        }
    ],
    "PHASE_TESTING": [
        {
            "task_type": "run_tests",
            "description": "Run tests and validate implementation",
            "priority": "high",
        }
    ],
    "PHASE_DEPLOYMENT": [
        {
            "task_type": "deploy",
            "description": "Deploy the implementation to target environment",
            "priority": "high",
        }
    ],
}

# Task type for dynamic PRD generation when no PRD exists
PRD_GENERATION_TASK = {
    "task_type": "generate_prd",
    "description": "Generate Product Requirements Document based on ticket description",
    "priority": "critical",
}


class PhaseProgressionService:
    """
    Orchestrates automatic phase progression and task spawning.

    Hook 1 (on task completion):
    - When a task completes, check if ALL tasks for the ticket's current phase are done
    - If all phase tasks are done, check phase gate requirements
    - If gate passes, auto-advance ticket to next phase

    Hook 2 (on phase transition):
    - When a ticket enters a new phase, spawn initial tasks for that phase
    - Check if ticket has a spec with pre-defined tasks for the phase
    - If yes, spawn those tasks; otherwise, spawn default phase tasks
    """

    def __init__(
        self,
        db: DatabaseService,
        task_queue: TaskQueueService,
        phase_gate: PhaseGateService,
        event_bus: Optional[EventBusService] = None,
        settings_service: Optional[SpecDrivenSettingsService] = None,
    ):
        """
        Initialize phase progression service.

        Args:
            db: Database service for queries
            task_queue: Task queue service for task operations
            phase_gate: Phase gate service for validation
            event_bus: Optional event bus for subscribing to events
            settings_service: Optional settings service for reading project settings
        """
        self.db = db
        self.task_queue = task_queue
        self.phase_gate = phase_gate
        self.event_bus = event_bus
        self.settings_service = settings_service or get_spec_driven_settings_service(db)
        self._workflow_orchestrator: Optional["TicketWorkflowOrchestrator"] = None

    def set_workflow_orchestrator(
        self, orchestrator: "TicketWorkflowOrchestrator"
    ) -> None:
        """Set the workflow orchestrator (to avoid circular imports)."""
        self._workflow_orchestrator = orchestrator

    def subscribe_to_events(self) -> None:
        """Subscribe to relevant events for phase progression hooks."""
        if not self.event_bus:
            logger.warning("No event bus available for phase progression hooks")
            return

        # Hook 0: Task started triggers ticket move to building (for implement_feature)
        self.event_bus.subscribe("TASK_STARTED", self._handle_task_started)

        # Hook 1: Task completion triggers phase advancement check
        self.event_bus.subscribe("TASK_COMPLETED", self._handle_task_completed)

        # Hook 2: Phase transition triggers task spawning
        self.event_bus.subscribe(
            "ticket.status_transitioned", self._handle_phase_transitioned
        )

        logger.info(
            "Phase progression hooks subscribed",
            hooks=["TASK_STARTED", "TASK_COMPLETED", "ticket.status_transitioned"],
        )

    # -------------------------------------------------------------------------
    # Hook 0: Move ticket to building when implement_feature task starts
    # -------------------------------------------------------------------------

    def _handle_task_started(self, event_data: dict) -> None:
        """
        Handle TASK_STARTED event to move ticket to building status.

        When an implement_feature task starts:
        1. Move ticket to building status (shows as "doing" on board)
        2. Publish status change event for real-time board update
        """
        try:
            task_id = event_data.get("entity_id")
            if not task_id:
                return

            payload = event_data.get("payload", {})
            ticket_id = payload.get("ticket_id")
            task_type = payload.get("task_type")

            if not ticket_id:
                logger.debug(
                    "Task started without ticket context",
                    task_id=task_id,
                )
                return

            # Only move ticket for implement_feature tasks
            if task_type == "implement_feature":
                logger.info(
                    "implement_feature task started, moving ticket to building",
                    task_id=task_id,
                    ticket_id=ticket_id,
                )
                self._move_ticket_to_building(ticket_id, task_id)

        except Exception as e:
            logger.error(
                "Error in Hook 0 (task started handler)",
                error=str(e),
                event_data=event_data,
            )

    def _move_ticket_to_building(self, ticket_id: str, task_id: str) -> bool:
        """
        Move a ticket to building status when implement_feature starts.

        Args:
            ticket_id: Ticket ID to move to building
            task_id: The task ID that triggered this (for logging)

        Returns:
            True if ticket was moved to building, False otherwise
        """
        from omoi_os.models.ticket_status import TicketStatus
        from omoi_os.utils.datetime import utc_now

        try:
            with self.db.get_session() as session:
                ticket = session.get(Ticket, ticket_id)
                if not ticket:
                    logger.warning(
                        "Ticket not found for building transition",
                        ticket_id=ticket_id,
                    )
                    return False

                # Skip if already building, done, or blocked
                if ticket.status in (TicketStatus.BUILDING.value, TicketStatus.DONE.value):
                    logger.debug(
                        "Ticket already in building or done status",
                        ticket_id=ticket_id,
                        current_status=ticket.status,
                    )
                    return False

                if ticket.is_blocked:
                    logger.warning(
                        "Cannot move blocked ticket to building",
                        ticket_id=ticket_id,
                    )
                    return False

                old_status = ticket.status
                ticket.status = TicketStatus.BUILDING.value
                # Sync phase_id to keep board column in sync
                ticket.phase_id = "PHASE_IMPLEMENTATION"
                ticket.updated_at = utc_now()

                session.commit()

                logger.info(
                    "Ticket moved to building after implement_feature started",
                    ticket_id=ticket_id,
                    task_id=task_id,
                    old_status=old_status,
                )

            # Publish ticket status change event (outside session)
            # Use TICKET_STATUS_CHANGED to match frontend expectations
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="TICKET_STATUS_CHANGED",
                        entity_type="ticket",
                        entity_id=str(ticket_id),
                        payload={
                            "from_status": old_status,
                            "to_status": TicketStatus.BUILDING.value,
                            "phase_id": "PHASE_IMPLEMENTATION",
                            "reason": f"implement_feature task {task_id} started",
                            "task_id": task_id,
                        },
                    )
                )

            return True

        except Exception as e:
            logger.error(
                "Error moving ticket to building",
                ticket_id=ticket_id,
                task_id=task_id,
                error=str(e),
            )
            return False

    # -------------------------------------------------------------------------
    # Hook 1: Auto-advance ticket when all phase tasks complete
    # -------------------------------------------------------------------------

    def _handle_task_completed(self, event_data: dict) -> None:
        """
        Handle TASK_COMPLETED event to check for phase completion.

        When a task completes:
        1. If it's an implement_feature task, move ticket directly to done
        2. Otherwise, check if all tasks in the ticket's current phase are done
        3. If so, validate phase gate and advance ticket
        """
        try:
            task_id = event_data.get("entity_id")
            if not task_id:
                return

            payload = event_data.get("payload", {})
            ticket_id = payload.get("ticket_id")
            phase_id = payload.get("phase_id")
            task_type = payload.get("task_type")

            if not ticket_id or not phase_id:
                logger.debug(
                    "Task completed without ticket/phase context",
                    task_id=task_id,
                )
                return

            logger.info(
                "Hook 1: Checking phase completion",
                task_id=task_id,
                ticket_id=ticket_id,
                phase_id=phase_id,
                task_type=task_type,
            )

            # Special case: implement_feature task completion moves ticket to done
            if task_type == "implement_feature":
                logger.info(
                    "implement_feature task completed, moving ticket to done",
                    task_id=task_id,
                    ticket_id=ticket_id,
                )
                self._move_ticket_to_done(ticket_id, task_id)
                return

            # Check if all phase tasks are complete
            if self._are_all_phase_tasks_complete(ticket_id, phase_id):
                logger.info(
                    "All phase tasks complete, attempting advancement",
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                )

                # Check auto_phase_progression setting before advancing
                project_id = self._get_ticket_project_id(ticket_id)
                settings = self.settings_service.get_settings(project_id)

                if not settings.auto_phase_progression:
                    logger.info(
                        "Auto-progression disabled for project, skipping advancement",
                        project_id=project_id,
                        ticket_id=ticket_id,
                        phase_id=phase_id,
                    )
                    return

                logger.debug(
                    "Auto-progression enabled, proceeding with advancement",
                    project_id=project_id,
                    ticket_id=ticket_id,
                )
                self._try_advance_ticket(ticket_id)
            else:
                logger.debug(
                    "Phase tasks still pending",
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                )

        except Exception as e:
            logger.error(
                "Error in Hook 1 (task completed handler)",
                error=str(e),
                event_data=event_data,
            )

    def _are_all_phase_tasks_complete(self, ticket_id: str, phase_id: str) -> bool:
        """Check if all tasks for a ticket in a specific phase are completed."""
        with self.db.get_session() as session:
            tasks = (
                session.query(Task)
                .filter(Task.ticket_id == ticket_id, Task.phase_id == phase_id)
                .all()
            )

            if not tasks:
                # No tasks means phase is "complete" (nothing to do)
                return True

            return all(task.status == "completed" for task in tasks)

    def _get_ticket_project_id(self, ticket_id: str) -> Optional[str]:
        """Get the project ID for a ticket.

        Args:
            ticket_id: The ticket ID to look up

        Returns:
            The project ID or None if ticket not found
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                logger.warning(
                    "Ticket not found when looking up project_id",
                    ticket_id=ticket_id,
                )
                return None
            return ticket.project_id

    def _try_advance_ticket(self, ticket_id: str) -> bool:
        """
        Try to advance ticket to next phase.

        Uses TicketWorkflowOrchestrator.check_and_progress_ticket()
        which validates phase gates before transitioning.

        Returns:
            True if ticket was advanced, False otherwise
        """
        if not self._workflow_orchestrator:
            logger.warning(
                "Workflow orchestrator not set, cannot advance ticket",
                ticket_id=ticket_id,
            )
            return False

        try:
            result = self._workflow_orchestrator.check_and_progress_ticket(ticket_id)
            if result:
                logger.info(
                    "Hook 1: Ticket auto-advanced",
                    ticket_id=ticket_id,
                    new_status=result.status,
                    new_phase=result.phase_id,
                )
                return True
            else:
                logger.debug(
                    "Ticket not ready for advancement (gate not passed)",
                    ticket_id=ticket_id,
                )
                return False
        except Exception as e:
            logger.error(
                "Error advancing ticket",
                ticket_id=ticket_id,
                error=str(e),
            )
            return False

    def _move_ticket_to_done(self, ticket_id: str, task_id: str) -> bool:
        """
        Move a ticket directly to done status when implement_feature completes.

        This bypasses the normal phase progression and moves the ticket
        directly to the done status, publishing the appropriate events.

        Args:
            ticket_id: Ticket ID to move to done
            task_id: The task ID that triggered this (for logging)

        Returns:
            True if ticket was moved to done, False otherwise
        """
        from omoi_os.models.ticket_status import TicketStatus
        from omoi_os.utils.datetime import utc_now

        try:
            with self.db.get_session() as session:
                ticket = session.get(Ticket, ticket_id)
                if not ticket:
                    logger.warning(
                        "Ticket not found for done transition",
                        ticket_id=ticket_id,
                    )
                    return False

                # Skip if already done or blocked
                if ticket.status == TicketStatus.DONE.value:
                    logger.debug(
                        "Ticket already done",
                        ticket_id=ticket_id,
                    )
                    return False

                if ticket.is_blocked:
                    logger.warning(
                        "Cannot move blocked ticket to done",
                        ticket_id=ticket_id,
                    )
                    return False

                old_status = ticket.status
                ticket.status = TicketStatus.DONE.value
                # Sync phase_id to keep board column in sync
                ticket.phase_id = "PHASE_DONE"
                ticket.updated_at = utc_now()

                session.commit()

                logger.info(
                    "Ticket moved to done after implement_feature completion",
                    ticket_id=ticket_id,
                    task_id=task_id,
                    old_status=old_status,
                )

            # Publish ticket status change event (outside session)
            # Use TICKET_STATUS_CHANGED to match frontend expectations
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="TICKET_STATUS_CHANGED",
                        entity_type="ticket",
                        entity_id=str(ticket_id),
                        payload={
                            "from_status": old_status,
                            "to_status": TicketStatus.DONE.value,
                            "phase_id": "PHASE_DONE",
                            "reason": f"implement_feature task {task_id} completed",
                            "task_id": task_id,
                        },
                    )
                )

            return True

        except Exception as e:
            logger.error(
                "Error moving ticket to done",
                ticket_id=ticket_id,
                task_id=task_id,
                error=str(e),
            )
            return False

    # -------------------------------------------------------------------------
    # Hook 2: Auto-spawn tasks when ticket enters new phase
    # -------------------------------------------------------------------------

    def _handle_phase_transitioned(self, event_data: dict) -> None:
        """
        Handle ticket.status_transitioned event to spawn phase tasks.

        When a ticket transitions to a new phase:
        1. Check if there are pre-defined tasks in the spec
        2. If yes, spawn those tasks
        3. If no, spawn default initial tasks for the phase
        """
        try:
            ticket_id = event_data.get("entity_id")
            if not ticket_id:
                return

            payload = event_data.get("payload", {})
            to_phase = payload.get("to_phase")
            from_phase = payload.get("from_phase")
            to_status = payload.get("to_status")

            if not to_phase:
                logger.debug(
                    "Phase transition without to_phase",
                    ticket_id=ticket_id,
                )
                return

            # Skip if transitioning to terminal phases or same phase
            if to_phase in ("PHASE_DONE", "PHASE_BLOCKED") or to_phase == from_phase:
                return

            logger.info(
                "Hook 2: Spawning tasks for new phase",
                ticket_id=ticket_id,
                from_phase=from_phase,
                to_phase=to_phase,
                to_status=to_status,
            )

            tasks_spawned = self._spawn_phase_tasks(ticket_id, to_phase)
            logger.info(
                "Hook 2: Phase tasks spawned",
                ticket_id=ticket_id,
                phase=to_phase,
                tasks_count=tasks_spawned,
            )

        except Exception as e:
            logger.error(
                "Error in Hook 2 (phase transitioned handler)",
                error=str(e),
                event_data=event_data,
            )

    def _spawn_phase_tasks(self, ticket_id: str, phase_id: str) -> int:
        """
        Spawn tasks for a ticket entering a new phase.

        Priority order:
        1. For PHASE_REQUIREMENTS without PRD: Spawn PRD generation task first
        2. Tasks defined in the ticket's spec (from .omoi_os directory)
        3. Default phase initial tasks

        Returns:
            Number of tasks spawned
        """
        # First, check if the ticket already has pending tasks for this phase
        with self.db.get_session() as session:
            existing_tasks = (
                session.query(Task)
                .filter(
                    Task.ticket_id == ticket_id,
                    Task.phase_id == phase_id,
                    Task.status.in_(["pending", "assigned", "running", "claiming"]),
                )
                .count()
            )

            if existing_tasks > 0:
                logger.debug(
                    "Phase already has pending tasks, skipping spawn",
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                    existing_tasks=existing_tasks,
                )
                return 0

            # Get ticket for priority and context
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                logger.warning("Ticket not found", ticket_id=ticket_id)
                return 0
            ticket_priority = ticket.priority or "medium"
            ticket_context = ticket.context or {}

        # Special handling for PHASE_REQUIREMENTS: Check if PRD exists
        if phase_id == "PHASE_REQUIREMENTS":
            has_prd = self._check_prd_exists(ticket_id, ticket_context)
            if not has_prd:
                logger.info(
                    "No PRD found for ticket, spawning PRD generation task",
                    ticket_id=ticket_id,
                )
                return self._spawn_prd_generation_task(ticket_id, ticket_priority)

        # Try to get tasks from spec
        spec_tasks = self._get_spec_tasks_for_phase(ticket_id, phase_id)

        if spec_tasks:
            return self._spawn_tasks_from_spec(ticket_id, phase_id, spec_tasks, ticket_priority)
        else:
            return self._spawn_default_phase_tasks(ticket_id, phase_id, ticket_priority)

    def _check_prd_exists(self, ticket_id: str, ticket_context: dict) -> bool:
        """
        Check if a PRD (Product Requirements Document) exists for this ticket.

        Checks:
        1. Ticket context for prd_url or requirements_document reference
        2. Phase gate artifacts for requirements_document type
        3. Spec files in .omoi_os directory (future integration)

        Returns:
            True if PRD exists, False otherwise
        """
        # Check ticket context for PRD reference
        if ticket_context.get("prd_url"):
            return True
        if ticket_context.get("requirements_document"):
            return True
        if ticket_context.get("spec_id"):
            return True

        # Check phase gate artifacts for requirements document
        from omoi_os.models.phase_gate_artifact import PhaseGateArtifact

        with self.db.get_session() as session:
            artifact = (
                session.query(PhaseGateArtifact)
                .filter(
                    PhaseGateArtifact.ticket_id == ticket_id,
                    PhaseGateArtifact.artifact_type == "requirements_document",
                )
                .first()
            )
            if artifact:
                return True

        # TODO: Check .omoi_os/specs/ directory for spec files
        # This would integrate with spec-driven-dev system

        return False

    def _spawn_prd_generation_task(self, ticket_id: str, priority: str) -> int:
        """
        Spawn a PRD generation task for a ticket without requirements.

        The PRD generation task will:
        1. Analyze the ticket title/description
        2. Determine if this is a feature (partial) or complete app request
        3. Generate appropriate requirements document
        4. Store the PRD in ticket context and/or as artifact

        Returns:
            Number of tasks spawned (1 on success, 0 on failure)
        """
        try:
            # Get ticket details to include in task description
            with self.db.get_session() as session:
                ticket = session.get(Ticket, ticket_id)
                if not ticket:
                    return 0
                ticket_title = ticket.title or "Untitled"
                ticket_description = ticket.description or ""

            # Create detailed task description
            task_description = (
                f"Generate Product Requirements Document for: {ticket_title}\n\n"
                f"Original Request:\n{ticket_description}\n\n"
                "Analyze whether this is a feature for an existing codebase or a new application, "
                "then generate appropriate requirements including:\n"
                "- Scope and objectives\n"
                "- Functional requirements\n"
                "- Non-functional requirements\n"
                "- Acceptance criteria\n"
                "- Dependencies and assumptions"
            )

            self.task_queue.enqueue_task(
                ticket_id=ticket_id,
                phase_id="PHASE_REQUIREMENTS",
                task_type=PRD_GENERATION_TASK["task_type"],
                description=task_description,
                priority=PRD_GENERATION_TASK["priority"],
                title=f"Generate PRD: {ticket_title[:50]}",
            )

            logger.info(
                "PRD generation task spawned",
                ticket_id=ticket_id,
                ticket_title=ticket_title,
            )
            return 1

        except Exception as e:
            logger.error(
                "Failed to spawn PRD generation task",
                ticket_id=ticket_id,
                error=str(e),
            )
            return 0

    def _get_spec_tasks_for_phase(
        self, ticket_id: str, phase_id: str
    ) -> list[dict[str, Any]]:
        """
        Get pre-defined tasks for a phase from the ticket's spec.

        Looks for tasks in .omoi_os/tasks/ that match:
        - The ticket ID
        - The target phase

        Returns:
            List of task definitions from spec, or empty list
        """
        # For now, this is a placeholder - will integrate with spec-driven-dev
        # The spec system stores tasks in .omoi_os/tasks/TSK-xxx.md format
        # We'll need to parse those and filter by ticket_id and phase_id

        # TODO: Integrate with spec-driven-dev parse_specs.py
        # For now, return empty to use default tasks
        return []

    def _spawn_tasks_from_spec(
        self,
        ticket_id: str,
        phase_id: str,
        spec_tasks: list[dict[str, Any]],
        priority: str,
    ) -> int:
        """Spawn tasks defined in the spec."""
        spawned = 0
        for task_def in spec_tasks:
            try:
                self.task_queue.enqueue_task(
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                    task_type=task_def.get("task_type", "implement"),
                    description=task_def.get("description", "Task from spec"),
                    priority=task_def.get("priority", priority),
                    dependencies=task_def.get("dependencies"),
                    title=task_def.get("title"),
                )
                spawned += 1
            except Exception as e:
                logger.error(
                    "Failed to spawn spec task",
                    ticket_id=ticket_id,
                    task_def=task_def,
                    error=str(e),
                )
        return spawned

    def _spawn_default_phase_tasks(
        self, ticket_id: str, phase_id: str, priority: str
    ) -> int:
        """Spawn default initial tasks for a phase."""
        task_defs = PHASE_INITIAL_TASKS.get(phase_id, [])

        if not task_defs:
            logger.debug(
                "No default tasks configured for phase",
                phase_id=phase_id,
            )
            return 0

        spawned = 0
        for task_def in task_defs:
            try:
                self.task_queue.enqueue_task(
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                    task_type=task_def["task_type"],
                    description=task_def["description"],
                    priority=task_def.get("priority", priority),
                    dependencies=task_def.get("dependencies"),
                )
                spawned += 1
            except Exception as e:
                logger.error(
                    "Failed to spawn default task",
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                    task_def=task_def,
                    error=str(e),
                )
        return spawned

    # -------------------------------------------------------------------------
    # Manual triggers (for testing and API use)
    # -------------------------------------------------------------------------

    def check_phase_completion(self, ticket_id: str) -> dict[str, Any]:
        """
        Manually check and attempt phase advancement for a ticket.

        Useful for:
        - Testing the Hook 1 logic
        - API endpoints to trigger phase checks
        - Recovery from missed events

        Returns:
            Dict with status information
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return {"error": "Ticket not found", "ticket_id": ticket_id}

            phase_id = ticket.phase_id
            status = ticket.status

        # Check if all phase tasks are complete
        all_complete = self._are_all_phase_tasks_complete(ticket_id, phase_id)

        result = {
            "ticket_id": ticket_id,
            "current_phase": phase_id,
            "current_status": status,
            "all_phase_tasks_complete": all_complete,
            "advanced": False,
        }

        if all_complete:
            advanced = self._try_advance_ticket(ticket_id)
            result["advanced"] = advanced
            if advanced:
                # Fetch new status
                with self.db.get_session() as session:
                    ticket = session.get(Ticket, ticket_id)
                    if ticket:
                        result["new_phase"] = ticket.phase_id
                        result["new_status"] = ticket.status

        return result

    def spawn_tasks_for_phase(
        self, ticket_id: str, phase_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Manually spawn tasks for a ticket's current or specified phase.

        Useful for:
        - Testing the Hook 2 logic
        - API endpoints to trigger task spawning
        - Recovery from missed phase transitions

        Returns:
            Dict with spawn information
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return {"error": "Ticket not found", "ticket_id": ticket_id}

            target_phase = phase_id or ticket.phase_id

        tasks_spawned = self._spawn_phase_tasks(ticket_id, target_phase)

        return {
            "ticket_id": ticket_id,
            "phase": target_phase,
            "tasks_spawned": tasks_spawned,
        }


# Singleton instance (lazy initialization)
_phase_progression_service: Optional[PhaseProgressionService] = None


def get_phase_progression_service(
    db: Optional[DatabaseService] = None,
    task_queue: Optional[TaskQueueService] = None,
    phase_gate: Optional[PhaseGateService] = None,
    event_bus: Optional[EventBusService] = None,
    settings_service: Optional[SpecDrivenSettingsService] = None,
) -> PhaseProgressionService:
    """Get or create the singleton phase progression service."""
    global _phase_progression_service

    if _phase_progression_service is None:
        if not all([db, task_queue, phase_gate]):
            raise ValueError(
                "Must provide db, task_queue, and phase_gate for first initialization"
            )
        _phase_progression_service = PhaseProgressionService(
            db=db,  # type: ignore
            task_queue=task_queue,  # type: ignore
            phase_gate=phase_gate,  # type: ignore
            event_bus=event_bus,
            settings_service=settings_service,
        )

    return _phase_progression_service
