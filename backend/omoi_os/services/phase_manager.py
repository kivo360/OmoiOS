"""Unified Phase Manager Service.

This service provides a centralized, authoritative source for all phase-related
operations including:
- Phase definitions and metadata
- Transition rules and validation
- Automatic progression callbacks
- Phase gate orchestration
- Status synchronization

The PhaseManager consolidates functionality from:
- PhaseProgressionService (hooks and task spawning)
- PhaseGateService (gate validation)
- TicketWorkflowOrchestrator (status transitions)

It provides clear, documented rules for phase transitions and ensures
consistency across the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
)

from omoi_os.logging import get_logger
from omoi_os.models.phase_gate_result import PhaseGateResult
from omoi_os.models.phase_history import PhaseHistory
from omoi_os.models.phases import Phase, PHASE_SEQUENCE, PHASE_TRANSITIONS
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.ticket_status import TicketStatus
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.services.context_service import ContextService
    from omoi_os.services.phase_gate import PhaseGateService
    from omoi_os.services.task_queue import TaskQueueService

logger = get_logger(__name__)


# =============================================================================
# Phase Configuration Data Classes
# =============================================================================


class ExecutionMode(StrEnum):
    """Execution modes that determine how tasks run."""

    EXPLORATION = "exploration"  # Stops early, doesn't push code
    IMPLEMENTATION = "implementation"  # Runs to completion, pushes code
    VALIDATION = "validation"  # Runs tests, validates functionality


@dataclass
class PhaseGateCriteria:
    """Criteria that must be met to exit a phase."""

    required_artifacts: List[str] = field(default_factory=list)
    all_tasks_completed: bool = True
    min_test_coverage: Optional[float] = None
    custom_validators: List[str] = field(default_factory=list)


@dataclass
class PhaseConfig:
    """Configuration for a single phase."""

    id: str
    name: str
    description: str
    sequence_order: int
    # Allowed next phases (excluding BLOCKED which is always allowed)
    allowed_transitions: Tuple[str, ...]
    # Status that tickets should have in this phase
    mapped_status: str
    # Execution mode for tasks in this phase
    execution_mode: ExecutionMode
    # Default task types to spawn when entering this phase
    default_task_types: List[str] = field(default_factory=list)
    # Gate criteria that must be met before exiting
    gate_criteria: Optional[PhaseGateCriteria] = None
    # Whether this is a terminal phase
    is_terminal: bool = False
    # Whether continuous mode is enabled (tasks run to completion)
    continuous_mode: bool = False
    # Whether to skip this phase (fast-track to next)
    skippable: bool = False


@dataclass
class TransitionResult:
    """Result of a phase transition attempt."""

    success: bool
    from_phase: str
    to_phase: Optional[str] = None
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    reason: Optional[str] = None
    blocking_reasons: List[str] = field(default_factory=list)
    artifacts_collected: int = 0
    tasks_spawned: int = 0


# =============================================================================
# Phase Registry - Single Source of Truth
# =============================================================================

# Map phases to their corresponding ticket statuses
PHASE_STATUS_MAP: Dict[str, str] = {
    "PHASE_BACKLOG": TicketStatus.BACKLOG.value,
    "PHASE_REQUIREMENTS": TicketStatus.ANALYZING.value,
    "PHASE_DESIGN": TicketStatus.ANALYZING.value,
    "PHASE_IMPLEMENTATION": TicketStatus.BUILDING.value,
    "PHASE_TESTING": TicketStatus.TESTING.value,
    "PHASE_DEPLOYMENT": TicketStatus.BUILDING_DONE.value,
    "PHASE_DONE": TicketStatus.DONE.value,
    "PHASE_BLOCKED": TicketStatus.BACKLOG.value,  # Blocked can be any status
}

# Reverse mapping: status to preferred phase
STATUS_PHASE_MAP: Dict[str, str] = {
    TicketStatus.BACKLOG.value: "PHASE_BACKLOG",
    TicketStatus.ANALYZING.value: "PHASE_REQUIREMENTS",
    TicketStatus.BUILDING.value: "PHASE_IMPLEMENTATION",
    TicketStatus.BUILDING_DONE.value: "PHASE_DEPLOYMENT",
    TicketStatus.TESTING.value: "PHASE_TESTING",
    TicketStatus.DONE.value: "PHASE_DONE",
}

# Next status progression (for automatic advancement)
STATUS_PROGRESSION: Dict[str, str] = {
    TicketStatus.BACKLOG.value: TicketStatus.ANALYZING.value,
    TicketStatus.ANALYZING.value: TicketStatus.BUILDING.value,
    TicketStatus.BUILDING.value: TicketStatus.BUILDING_DONE.value,
    TicketStatus.BUILDING_DONE.value: TicketStatus.TESTING.value,
    TicketStatus.TESTING.value: TicketStatus.DONE.value,
}

# Complete phase configuration registry
PHASE_CONFIGS: Dict[str, PhaseConfig] = {
    "PHASE_BACKLOG": PhaseConfig(
        id="PHASE_BACKLOG",
        name="Backlog",
        description="Ticket is queued but not yet being worked on",
        sequence_order=0,
        allowed_transitions=("PHASE_REQUIREMENTS", "PHASE_IMPLEMENTATION"),
        mapped_status=TicketStatus.BACKLOG.value,
        execution_mode=ExecutionMode.EXPLORATION,
        default_task_types=[],
        is_terminal=False,
        continuous_mode=False,
        skippable=True,  # Can skip directly to implementation
    ),
    "PHASE_REQUIREMENTS": PhaseConfig(
        id="PHASE_REQUIREMENTS",
        name="Requirements",
        description="Analyzing and documenting requirements",
        sequence_order=1,
        allowed_transitions=("PHASE_DESIGN", "PHASE_IMPLEMENTATION"),
        mapped_status=TicketStatus.ANALYZING.value,
        execution_mode=ExecutionMode.EXPLORATION,
        default_task_types=["analyze_requirements", "generate_prd"],
        gate_criteria=PhaseGateCriteria(
            required_artifacts=["requirements_document"],
            all_tasks_completed=True,
        ),
        continuous_mode=False,
        skippable=True,  # Can skip to implementation
    ),
    "PHASE_DESIGN": PhaseConfig(
        id="PHASE_DESIGN",
        name="Design",
        description="Creating technical design and architecture",
        sequence_order=2,
        allowed_transitions=("PHASE_IMPLEMENTATION",),
        mapped_status=TicketStatus.ANALYZING.value,
        execution_mode=ExecutionMode.EXPLORATION,
        default_task_types=["create_design"],
        gate_criteria=PhaseGateCriteria(
            required_artifacts=["design_document"],
            all_tasks_completed=True,
        ),
        continuous_mode=False,
        skippable=True,  # Can skip to implementation
    ),
    "PHASE_IMPLEMENTATION": PhaseConfig(
        id="PHASE_IMPLEMENTATION",
        name="Implementation",
        description="Building the feature or fix",
        sequence_order=3,
        allowed_transitions=("PHASE_TESTING", "PHASE_DONE"),
        mapped_status=TicketStatus.BUILDING.value,
        execution_mode=ExecutionMode.IMPLEMENTATION,
        default_task_types=["implement_feature"],
        gate_criteria=PhaseGateCriteria(
            required_artifacts=["code_changes"],
            all_tasks_completed=True,
            min_test_coverage=80.0,
        ),
        continuous_mode=True,  # Tasks run to completion
        skippable=False,
    ),
    "PHASE_TESTING": PhaseConfig(
        id="PHASE_TESTING",
        name="Testing",
        description="Validating the implementation",
        sequence_order=4,
        allowed_transitions=("PHASE_DEPLOYMENT", "PHASE_IMPLEMENTATION", "PHASE_DONE"),
        mapped_status=TicketStatus.TESTING.value,
        execution_mode=ExecutionMode.VALIDATION,
        default_task_types=["run_tests", "write_tests"],
        gate_criteria=PhaseGateCriteria(
            required_artifacts=["test_results"],
            all_tasks_completed=True,
            custom_validators=["all_tests_passing"],
        ),
        continuous_mode=True,
        skippable=False,
    ),
    "PHASE_DEPLOYMENT": PhaseConfig(
        id="PHASE_DEPLOYMENT",
        name="Deployment",
        description="Deploying to target environment",
        sequence_order=5,
        allowed_transitions=("PHASE_DONE",),
        mapped_status=TicketStatus.BUILDING_DONE.value,
        execution_mode=ExecutionMode.IMPLEMENTATION,
        default_task_types=["deploy"],
        gate_criteria=PhaseGateCriteria(
            required_artifacts=["deployment_evidence"],
            all_tasks_completed=True,
        ),
        continuous_mode=True,
        skippable=True,  # Can skip if not deploying
    ),
    "PHASE_DONE": PhaseConfig(
        id="PHASE_DONE",
        name="Done",
        description="Work is complete",
        sequence_order=6,
        allowed_transitions=(),
        mapped_status=TicketStatus.DONE.value,
        execution_mode=ExecutionMode.EXPLORATION,
        is_terminal=True,
        continuous_mode=False,
        skippable=False,
    ),
    "PHASE_BLOCKED": PhaseConfig(
        id="PHASE_BLOCKED",
        name="Blocked",
        description="Work is blocked by external dependency",
        sequence_order=99,
        allowed_transitions=(
            "PHASE_BACKLOG",
            "PHASE_REQUIREMENTS",
            "PHASE_DESIGN",
            "PHASE_IMPLEMENTATION",
            "PHASE_TESTING",
        ),
        mapped_status=TicketStatus.BACKLOG.value,
        execution_mode=ExecutionMode.EXPLORATION,
        is_terminal=True,  # Blocked is a terminal state until unblocked
        continuous_mode=False,
        skippable=False,
    ),
}

# Task types that enable continuous mode (run to completion)
CONTINUOUS_TASK_TYPES = frozenset({
    "implement_feature",
    "fix_bug",
    "write_tests",
    "refactor",
    "deploy",
})

# Task types that run in exploration mode (stop early)
EXPLORATION_TASK_TYPES = frozenset({
    "analyze_requirements",
    "analyze_codebase",
    "explore_problem",
    "generate_prd",
    "create_design",
})


# =============================================================================
# Callback Types
# =============================================================================

PhaseCallback = Callable[["PhaseManager", str, str, str], None]


# =============================================================================
# Phase Manager Service
# =============================================================================


class PhaseManager:
    """
    Unified Phase Manager for orchestrating ticket phase transitions.

    This service provides:
    1. Single source of truth for phase configurations
    2. Validation of all phase transitions
    3. Automatic status synchronization
    4. Callback hooks for pre/post transition logic
    5. Integration with phase gates and task spawning

    Usage:
        manager = PhaseManager(db, task_queue, phase_gate, event_bus)

        # Check if transition is allowed
        can, reasons = manager.can_transition(ticket_id, "PHASE_IMPLEMENTATION")

        # Perform transition with validation
        result = manager.transition_to_phase(ticket_id, "PHASE_IMPLEMENTATION")

        # Auto-advance based on gate criteria
        result = manager.check_and_advance(ticket_id)

        # Fast-track to implementation (skip requirements/design)
        result = manager.fast_track_to_implementation(ticket_id)
    """

    def __init__(
        self,
        db: DatabaseService,
        task_queue: Optional["TaskQueueService"] = None,
        phase_gate: Optional["PhaseGateService"] = None,
        event_bus: Optional[EventBusService] = None,
        context_service: Optional["ContextService"] = None,
    ):
        """
        Initialize the phase manager.

        Args:
            db: Database service for persistence
            task_queue: Optional task queue for spawning tasks
            phase_gate: Optional phase gate service for validation
            event_bus: Optional event bus for publishing events
            context_service: Optional context service for phase context propagation
        """
        self.db = db
        self.task_queue = task_queue
        self.phase_gate = phase_gate
        self.event_bus = event_bus
        self._context_service = context_service

        # Callback registries
        self._pre_transition_callbacks: List[PhaseCallback] = []
        self._post_transition_callbacks: List[PhaseCallback] = []
        self._on_gate_failure_callbacks: List[PhaseCallback] = []

        logger.info("PhaseManager initialized")

    @property
    def context_service(self) -> Optional["ContextService"]:
        """Get context service, creating lazily if needed."""
        if self._context_service is None:
            try:
                from omoi_os.services.context_service import ContextService
                self._context_service = ContextService(self.db)
            except Exception as e:
                logger.warning("Could not create ContextService", error=str(e))
        return self._context_service

    # -------------------------------------------------------------------------
    # Configuration Access
    # -------------------------------------------------------------------------

    def get_phase_config(self, phase_id: str) -> Optional[PhaseConfig]:
        """Get configuration for a phase."""
        return PHASE_CONFIGS.get(phase_id)

    def get_all_phases(self) -> List[PhaseConfig]:
        """Get all phase configurations in sequence order."""
        return sorted(PHASE_CONFIGS.values(), key=lambda p: p.sequence_order)

    def get_status_for_phase(self, phase_id: str) -> Optional[str]:
        """Get the ticket status corresponding to a phase."""
        config = self.get_phase_config(phase_id)
        return config.mapped_status if config else None

    def get_phase_for_status(self, status: str) -> Optional[str]:
        """Get the preferred phase for a ticket status."""
        return STATUS_PHASE_MAP.get(status)

    def get_execution_mode(self, phase_id: str) -> ExecutionMode:
        """Get the execution mode for a phase."""
        config = self.get_phase_config(phase_id)
        return config.execution_mode if config else ExecutionMode.EXPLORATION

    def is_continuous_mode_enabled(self, phase_id: str) -> bool:
        """Check if continuous mode is enabled for a phase."""
        config = self.get_phase_config(phase_id)
        return config.continuous_mode if config else False

    def get_next_phase(self, current_phase: str) -> Optional[str]:
        """Get the next phase in the standard progression."""
        config = self.get_phase_config(current_phase)
        if not config or config.is_terminal:
            return None

        # Return first allowed transition (standard progression)
        if config.allowed_transitions:
            return config.allowed_transitions[0]
        return None

    def get_next_status(self, current_status: str) -> Optional[str]:
        """Get the next status in the standard progression."""
        return STATUS_PROGRESSION.get(current_status)

    # -------------------------------------------------------------------------
    # Transition Validation
    # -------------------------------------------------------------------------

    def can_transition(
        self, ticket_id: str, to_phase: str
    ) -> Tuple[bool, List[str]]:
        """
        Check if a ticket can transition to a target phase.

        Args:
            ticket_id: The ticket ID
            to_phase: The target phase

        Returns:
            Tuple of (can_transition, list of blocking reasons)
        """
        blocking_reasons: List[str] = []

        # Get current ticket state
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return False, [f"Ticket {ticket_id} not found"]

            current_phase = ticket.phase_id
            is_blocked = ticket.is_blocked

        # Check if target phase exists
        to_config = self.get_phase_config(to_phase)
        if not to_config:
            return False, [f"Unknown target phase: {to_phase}"]

        # Check if blocked
        if is_blocked and to_phase != "PHASE_BLOCKED":
            # When blocked, can only transition to unblock phases
            blocked_config = self.get_phase_config("PHASE_BLOCKED")
            if blocked_config and to_phase not in blocked_config.allowed_transitions:
                blocking_reasons.append(
                    f"Ticket is blocked. Can only transition to: "
                    f"{blocked_config.allowed_transitions}"
                )

        # Get current phase config
        from_config = self.get_phase_config(current_phase)
        if from_config:
            # Check if transition is allowed
            allowed = list(from_config.allowed_transitions) + ["PHASE_BLOCKED"]
            if to_phase not in allowed:
                blocking_reasons.append(
                    f"Transition from {current_phase} to {to_phase} not allowed. "
                    f"Allowed transitions: {allowed}"
                )

        # Check phase gate if configured
        if from_config and from_config.gate_criteria and self.phase_gate:
            gate_check = self.phase_gate.check_gate_requirements(
                ticket_id, current_phase
            )
            if not gate_check.get("requirements_met"):
                missing = gate_check.get("missing_artifacts", [])
                if missing:
                    blocking_reasons.append(
                        f"Phase gate requirements not met. Missing: {missing}"
                    )
                if gate_check.get("validation_status") == "waiting_tasks":
                    blocking_reasons.append("Not all phase tasks are completed")

        return len(blocking_reasons) == 0, blocking_reasons

    def validate_transition_path(
        self, from_phase: str, to_phase: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate if a transition path is allowed without checking ticket state.

        Args:
            from_phase: Source phase
            to_phase: Target phase

        Returns:
            Tuple of (valid, reasons if invalid)
        """
        from_config = self.get_phase_config(from_phase)
        to_config = self.get_phase_config(to_phase)

        if not from_config:
            return False, [f"Unknown source phase: {from_phase}"]
        if not to_config:
            return False, [f"Unknown target phase: {to_phase}"]

        # Always allow BLOCKED
        if to_phase == "PHASE_BLOCKED":
            return True, []

        # Check if in allowed transitions
        if to_phase in from_config.allowed_transitions:
            return True, []

        return False, [
            f"Transition from {from_phase} to {to_phase} not allowed. "
            f"Allowed: {from_config.allowed_transitions}"
        ]

    # -------------------------------------------------------------------------
    # Phase Transitions
    # -------------------------------------------------------------------------

    def transition_to_phase(
        self,
        ticket_id: str,
        to_phase: str,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        force: bool = False,
        spawn_tasks: bool = True,
    ) -> TransitionResult:
        """
        Transition a ticket to a new phase.

        This method:
        1. Validates the transition is allowed
        2. Collects artifacts from current phase
        3. Updates ticket phase and status
        4. Records phase history
        5. Publishes transition event
        6. Spawns initial tasks for new phase (optional)

        Args:
            ticket_id: The ticket ID
            to_phase: Target phase
            initiated_by: Who initiated the transition
            reason: Reason for transition
            force: Skip validation if True
            spawn_tasks: Whether to spawn tasks for new phase

        Returns:
            TransitionResult with success status and details
        """
        # Pre-transition validation
        if not force:
            can, reasons = self.can_transition(ticket_id, to_phase)
            if not can:
                return TransitionResult(
                    success=False,
                    from_phase="",
                    to_phase=to_phase,
                    blocking_reasons=reasons,
                    reason="Transition validation failed",
                )

        # Execute pre-transition callbacks
        for callback in self._pre_transition_callbacks:
            try:
                with self.db.get_session() as session:
                    ticket = session.get(Ticket, ticket_id)
                    if ticket:
                        callback(self, ticket_id, ticket.phase_id, to_phase)
            except Exception as e:
                logger.error(
                    "Pre-transition callback failed",
                    callback=callback.__name__,
                    error=str(e),
                )

        # Collect artifacts from current phase
        artifacts_collected = 0
        if self.phase_gate:
            try:
                with self.db.get_session() as session:
                    ticket = session.get(Ticket, ticket_id)
                    if ticket:
                        artifacts = self.phase_gate.collect_artifacts(
                            ticket_id, ticket.phase_id
                        )
                        artifacts_collected = len(artifacts)
            except Exception as e:
                logger.warning(
                    "Artifact collection failed",
                    ticket_id=ticket_id,
                    error=str(e),
                )

        # Aggregate context from current phase before transitioning
        # This ensures the context from the current phase is saved and available
        # for the next phase's tasks
        from_phase_context = None
        if self.context_service:
            try:
                with self.db.get_session() as session:
                    ticket = session.get(Ticket, ticket_id)
                    if ticket:
                        current_phase = ticket.phase_id
                        # Update ticket context with aggregated phase data
                        self.context_service.update_ticket_context(ticket_id, current_phase)
                        # Get context to pass to spawned tasks
                        from_phase_context = self.context_service.get_context_for_phase(
                            ticket_id, to_phase
                        )
                        logger.debug(
                            "Phase context aggregated for transition",
                            ticket_id=ticket_id,
                            from_phase=current_phase,
                            to_phase=to_phase,
                            context_phases=list(from_phase_context.get("phases", {}).keys()),
                        )
            except Exception as e:
                logger.warning(
                    "Context aggregation failed during phase transition",
                    ticket_id=ticket_id,
                    error=str(e),
                )

        # Perform the transition
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return TransitionResult(
                    success=False,
                    from_phase="",
                    blocking_reasons=[f"Ticket {ticket_id} not found"],
                )

            from_phase = ticket.phase_id
            from_status = ticket.status

            # Update phase
            ticket.previous_phase_id = from_phase
            ticket.phase_id = to_phase

            # Sync status with phase
            to_config = self.get_phase_config(to_phase)
            if to_config:
                ticket.status = to_config.mapped_status

            # Clear blocked if unblocking
            if ticket.is_blocked and to_phase in PHASE_CONFIGS.get(
                "PHASE_BLOCKED", PhaseConfig(
                    id="", name="", description="", sequence_order=0,
                    allowed_transitions=(), mapped_status="", execution_mode=ExecutionMode.EXPLORATION
                )
            ).allowed_transitions:
                ticket.is_blocked = False
                ticket.blocked_reason = None
                ticket.blocked_at = None

            ticket.updated_at = utc_now()

            # Record phase history
            history = PhaseHistory(
                ticket_id=ticket_id,
                from_phase=from_phase,
                to_phase=to_phase,
                transition_reason=reason or f"Phase transition: {from_phase} → {to_phase}",
                transitioned_by=initiated_by or "phase-manager",
            )
            session.add(history)

            session.commit()
            to_status = ticket.status

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="ticket.phase_transitioned",
                    entity_type="ticket",
                    entity_id=ticket_id,
                    payload={
                        "from_phase": from_phase,
                        "to_phase": to_phase,
                        "from_status": from_status,
                        "to_status": to_status,
                        "initiated_by": initiated_by,
                        "reason": reason,
                    },
                )
            )

            # Also publish status changed for board updates
            self.event_bus.publish(
                SystemEvent(
                    event_type="TICKET_STATUS_CHANGED",
                    entity_type="ticket",
                    entity_id=ticket_id,
                    payload={
                        "from_status": from_status,
                        "to_status": to_status,
                        "phase_id": to_phase,
                        "reason": reason or f"Phase transition: {from_phase} → {to_phase}",
                    },
                )
            )

        # Spawn tasks for new phase with context from prior phases
        tasks_spawned = 0
        if spawn_tasks and self.task_queue and to_config and not to_config.is_terminal:
            tasks_spawned = self._spawn_phase_tasks(
                ticket_id, to_phase, prior_context=from_phase_context
            )

        # Execute post-transition callbacks
        for callback in self._post_transition_callbacks:
            try:
                callback(self, ticket_id, from_phase, to_phase)
            except Exception as e:
                logger.error(
                    "Post-transition callback failed",
                    callback=callback.__name__,
                    error=str(e),
                )

        logger.info(
            "Phase transition completed",
            ticket_id=ticket_id,
            from_phase=from_phase,
            to_phase=to_phase,
            tasks_spawned=tasks_spawned,
            artifacts_collected=artifacts_collected,
        )

        return TransitionResult(
            success=True,
            from_phase=from_phase,
            to_phase=to_phase,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            artifacts_collected=artifacts_collected,
            tasks_spawned=tasks_spawned,
        )

    def check_and_advance(self, ticket_id: str) -> TransitionResult:
        """
        Check if a ticket can advance and advance if possible.

        This method checks phase gate criteria and automatically
        advances the ticket if all requirements are met.

        Args:
            ticket_id: The ticket ID

        Returns:
            TransitionResult with success status
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return TransitionResult(
                    success=False,
                    from_phase="",
                    blocking_reasons=[f"Ticket {ticket_id} not found"],
                )

            current_phase = ticket.phase_id
            is_blocked = ticket.is_blocked

        # Don't advance blocked or terminal tickets
        config = self.get_phase_config(current_phase)
        if not config or config.is_terminal or is_blocked:
            return TransitionResult(
                success=False,
                from_phase=current_phase,
                reason="Ticket is blocked or in terminal phase",
            )

        # Check if we can advance
        next_phase = self.get_next_phase(current_phase)
        if not next_phase:
            return TransitionResult(
                success=False,
                from_phase=current_phase,
                reason="No next phase available",
            )

        # Validate transition
        can, reasons = self.can_transition(ticket_id, next_phase)
        if not can:
            # Execute gate failure callbacks
            for callback in self._on_gate_failure_callbacks:
                try:
                    callback(self, ticket_id, current_phase, next_phase)
                except Exception as e:
                    logger.error(
                        "Gate failure callback failed",
                        callback=callback.__name__,
                        error=str(e),
                    )

            return TransitionResult(
                success=False,
                from_phase=current_phase,
                to_phase=next_phase,
                blocking_reasons=reasons,
                reason="Phase gate criteria not met",
            )

        # Perform transition
        return self.transition_to_phase(
            ticket_id,
            next_phase,
            initiated_by="phase-manager-auto-advance",
            reason="Automatic advancement: phase gate criteria met",
        )

    def fast_track_to_implementation(
        self,
        ticket_id: str,
        initiated_by: Optional[str] = None,
    ) -> TransitionResult:
        """
        Fast-track a ticket directly to implementation phase.

        This skips requirements and design phases for tickets that
        are ready for immediate implementation.

        Args:
            ticket_id: The ticket ID
            initiated_by: Who initiated the fast-track

        Returns:
            TransitionResult with success status
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return TransitionResult(
                    success=False,
                    from_phase="",
                    blocking_reasons=[f"Ticket {ticket_id} not found"],
                )

            current_phase = ticket.phase_id

        # Check if already in implementation or beyond
        if current_phase in ("PHASE_IMPLEMENTATION", "PHASE_TESTING", "PHASE_DEPLOYMENT", "PHASE_DONE"):
            return TransitionResult(
                success=False,
                from_phase=current_phase,
                reason=f"Ticket already in {current_phase}",
            )

        # Check if current phase allows fast-track
        config = self.get_phase_config(current_phase)
        if config and "PHASE_IMPLEMENTATION" in config.allowed_transitions:
            return self.transition_to_phase(
                ticket_id,
                "PHASE_IMPLEMENTATION",
                initiated_by=initiated_by or "phase-manager-fast-track",
                reason="Fast-tracked to implementation",
            )

        # Otherwise do sequential transitions
        logger.info(
            "Fast-tracking ticket to implementation",
            ticket_id=ticket_id,
            from_phase=current_phase,
        )

        return self.transition_to_phase(
            ticket_id,
            "PHASE_IMPLEMENTATION",
            initiated_by=initiated_by or "phase-manager-fast-track",
            reason="Fast-tracked to implementation",
            force=True,  # Force the transition
        )

    def move_to_done(
        self,
        ticket_id: str,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> TransitionResult:
        """
        Move a ticket directly to done phase.

        This is typically called when an implement_feature task completes.

        Args:
            ticket_id: The ticket ID
            initiated_by: Who initiated the completion
            reason: Reason for completion

        Returns:
            TransitionResult with success status
        """
        return self.transition_to_phase(
            ticket_id,
            "PHASE_DONE",
            initiated_by=initiated_by or "phase-manager",
            reason=reason or "Work completed",
            force=True,  # Skip gate validation for completion
            spawn_tasks=False,
        )

    # -------------------------------------------------------------------------
    # Task Spawning
    # -------------------------------------------------------------------------

    def _spawn_phase_tasks(
        self,
        ticket_id: str,
        phase_id: str,
        prior_context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Spawn initial tasks for a phase.

        Args:
            ticket_id: The ticket ID
            phase_id: The phase to spawn tasks for
            prior_context: Optional context from prior phases

        Returns:
            Number of tasks spawned
        """
        if not self.task_queue:
            return 0

        config = self.get_phase_config(phase_id)
        if not config or not config.default_task_types:
            return 0

        # Check if tasks already exist for this phase
        with self.db.get_session() as session:
            existing = (
                session.query(Task)
                .filter(
                    Task.ticket_id == ticket_id,
                    Task.phase_id == phase_id,
                    Task.status.in_(["pending", "assigned", "running", "claiming"]),
                )
                .count()
            )

            if existing > 0:
                logger.debug(
                    "Phase already has pending tasks",
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                    existing_tasks=existing,
                )
                return 0

            # Get ticket for context
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return 0
            ticket_priority = ticket.priority or "medium"
            ticket_title = ticket.title or "Task"

        # Build description with prior context summary if available
        context_summary = ""
        if prior_context and prior_context.get("summary"):
            context_summary = f"\n\nPrior phase context:\n{prior_context['summary']}"

        spawned = 0
        for task_type in config.default_task_types:
            try:
                description = f"{task_type} for: {ticket_title}{context_summary}"
                self.task_queue.enqueue_task(
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                    task_type=task_type,
                    description=description,
                    priority=ticket_priority,
                    title=f"{task_type}: {ticket_title[:50]}",
                )
                spawned += 1
            except Exception as e:
                logger.error(
                    "Failed to spawn task",
                    ticket_id=ticket_id,
                    phase_id=phase_id,
                    task_type=task_type,
                    error=str(e),
                )

        logger.info(
            "Spawned phase tasks",
            ticket_id=ticket_id,
            phase_id=phase_id,
            tasks_spawned=spawned,
        )

        return spawned

    # -------------------------------------------------------------------------
    # Callback Registration
    # -------------------------------------------------------------------------

    def register_pre_transition_callback(self, callback: PhaseCallback) -> None:
        """Register a callback to run before phase transitions."""
        self._pre_transition_callbacks.append(callback)
        logger.debug("Registered pre-transition callback", callback=callback.__name__)

    def register_post_transition_callback(self, callback: PhaseCallback) -> None:
        """Register a callback to run after phase transitions."""
        self._post_transition_callbacks.append(callback)
        logger.debug("Registered post-transition callback", callback=callback.__name__)

    def register_gate_failure_callback(self, callback: PhaseCallback) -> None:
        """Register a callback to run when phase gate validation fails."""
        self._on_gate_failure_callbacks.append(callback)
        logger.debug("Registered gate failure callback", callback=callback.__name__)

    # -------------------------------------------------------------------------
    # Event Subscriptions
    # -------------------------------------------------------------------------

    def subscribe_to_events(self) -> None:
        """Subscribe to relevant events for automatic phase management."""
        if not self.event_bus:
            logger.warning("No event bus available for phase manager hooks")
            return

        # Task started: Move ticket to appropriate phase status
        self.event_bus.subscribe("TASK_STARTED", self._handle_task_started)

        # Task completed: Check for phase advancement
        self.event_bus.subscribe("TASK_COMPLETED", self._handle_task_completed)

        logger.info(
            "Phase manager subscribed to events",
            events=["TASK_STARTED", "TASK_COMPLETED"],
        )

    def _handle_task_started(self, event_data: dict) -> None:
        """Handle task started event to update ticket status."""
        try:
            payload = event_data.get("payload", {})
            ticket_id = payload.get("ticket_id")
            task_type = payload.get("task_type")
            phase_id = payload.get("phase_id")

            if not ticket_id:
                return

            # For implementation tasks, ensure ticket is in building status
            if task_type in CONTINUOUS_TASK_TYPES:
                with self.db.get_session() as session:
                    ticket = session.get(Ticket, ticket_id)
                    if not ticket or ticket.is_blocked:
                        return

                    # If task is implementation type, ensure we're in implementation phase
                    if task_type == "implement_feature" and ticket.phase_id != "PHASE_IMPLEMENTATION":
                        logger.info(
                            "Moving ticket to implementation for implement_feature task",
                            ticket_id=ticket_id,
                        )

                # Move to implementation if needed
                self.transition_to_phase(
                    ticket_id,
                    "PHASE_IMPLEMENTATION",
                    initiated_by="phase-manager-task-started",
                    reason=f"Task {task_type} started",
                    spawn_tasks=False,
                )

        except Exception as e:
            logger.error(
                "Error handling task started event",
                error=str(e),
                event_data=event_data,
            )

    def _handle_task_completed(self, event_data: dict) -> None:
        """Handle task completed event to check for phase advancement."""
        try:
            payload = event_data.get("payload", {})
            ticket_id = payload.get("ticket_id")
            task_type = payload.get("task_type")

            if not ticket_id:
                return

            # For implement_feature, move directly to done
            if task_type == "implement_feature":
                logger.info(
                    "implement_feature completed, moving to done",
                    ticket_id=ticket_id,
                )
                self.move_to_done(
                    ticket_id,
                    initiated_by="phase-manager-task-completed",
                    reason=f"Task {task_type} completed",
                )
                return

            # For other tasks, check if we can advance
            self.check_and_advance(ticket_id)

        except Exception as e:
            logger.error(
                "Error handling task completed event",
                error=str(e),
                event_data=event_data,
            )

    # -------------------------------------------------------------------------
    # Status Synchronization
    # -------------------------------------------------------------------------

    def sync_status_with_phase(self, ticket_id: str) -> bool:
        """
        Ensure ticket status matches its phase.

        Args:
            ticket_id: The ticket ID

        Returns:
            True if status was updated
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return False

            expected_status = self.get_status_for_phase(ticket.phase_id)
            if expected_status and ticket.status != expected_status:
                old_status = ticket.status
                ticket.status = expected_status
                ticket.updated_at = utc_now()
                session.commit()

                logger.info(
                    "Synced ticket status with phase",
                    ticket_id=ticket_id,
                    phase=ticket.phase_id,
                    old_status=old_status,
                    new_status=expected_status,
                )
                return True

        return False

    def sync_phase_with_status(self, ticket_id: str) -> bool:
        """
        Ensure ticket phase matches its status.

        Args:
            ticket_id: The ticket ID

        Returns:
            True if phase was updated
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return False

            expected_phase = self.get_phase_for_status(ticket.status)
            if expected_phase and ticket.phase_id != expected_phase:
                old_phase = ticket.phase_id
                ticket.phase_id = expected_phase
                ticket.updated_at = utc_now()
                session.commit()

                logger.info(
                    "Synced ticket phase with status",
                    ticket_id=ticket_id,
                    status=ticket.status,
                    old_phase=old_phase,
                    new_phase=expected_phase,
                )
                return True

        return False


# =============================================================================
# Singleton Access
# =============================================================================

_phase_manager: Optional[PhaseManager] = None


def get_phase_manager(
    db: Optional[DatabaseService] = None,
    task_queue: Optional["TaskQueueService"] = None,
    phase_gate: Optional["PhaseGateService"] = None,
    event_bus: Optional[EventBusService] = None,
    context_service: Optional["ContextService"] = None,
) -> PhaseManager:
    """Get or create the singleton PhaseManager instance."""
    global _phase_manager

    if _phase_manager is None:
        if db is None:
            raise ValueError("Must provide db for first initialization")
        _phase_manager = PhaseManager(
            db=db,
            task_queue=task_queue,
            phase_gate=phase_gate,
            event_bus=event_bus,
            context_service=context_service,
        )

    return _phase_manager


def reset_phase_manager() -> None:
    """Reset the singleton for testing."""
    global _phase_manager
    _phase_manager = None
