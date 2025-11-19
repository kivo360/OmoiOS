"""Ticket workflow orchestrator for Kanban state machine enforcement."""

from datetime import timedelta
from typing import Any, Dict, List, Optional

from omoi_os.models.phase_history import PhaseHistory
from omoi_os.models.ticket import Ticket
from omoi_os.models.ticket_status import (
    BLOCKED_TRANSITIONS,
    TicketStatus,
    is_valid_transition,
)
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.pydantic_ai_service import PydanticAIService
from omoi_os.schemas.blocker_analysis import BlockerAnalysis
from omoi_os.utils.datetime import utc_now


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


class TicketBlockedError(Exception):
    """Raised when ticket is blocked and cannot transition."""


class TicketWorkflowOrchestrator:
    """
    Ticket Workflow Orchestrator per REQ-TKT-SM-001 through REQ-TKT-BL-003.

    Enforces Kanban state machine, orchestrates phase transitions, manages
    ticket-to-task relationships, and coordinates with Task Queue and Validation systems.
    """

    # Configuration constants
    BLOCKING_THRESHOLD_MINUTES = 30  # REQ-TKT-BL-001 default
    MAX_RETRY_ATTEMPTS = 3

    # Phase to status mapping
    PHASE_TO_STATUS: Dict[str, str] = {
        "PHASE_BACKLOG": TicketStatus.BACKLOG.value,
        "PHASE_REQUIREMENTS": TicketStatus.ANALYZING.value,
        "PHASE_DESIGN": TicketStatus.ANALYZING.value,
        "PHASE_IMPLEMENTATION": TicketStatus.BUILDING.value,
        "PHASE_TESTING": TicketStatus.TESTING.value,
        "PHASE_DEPLOYMENT": TicketStatus.DONE.value,
    }

    # Status to phase mapping (reverse lookup)
    STATUS_TO_PHASE: Dict[str, str] = {
        TicketStatus.BACKLOG.value: "PHASE_BACKLOG",
        TicketStatus.ANALYZING.value: "PHASE_REQUIREMENTS",
        TicketStatus.BUILDING.value: "PHASE_IMPLEMENTATION",
        TicketStatus.BUILDING_DONE.value: "PHASE_IMPLEMENTATION",  # Same phase
        TicketStatus.TESTING.value: "PHASE_TESTING",
        TicketStatus.DONE.value: "PHASE_DEPLOYMENT",
    }

    def __init__(
        self,
        db: DatabaseService,
        task_queue: TaskQueueService,
        phase_gate: PhaseGateService,
        event_bus: Optional[EventBusService] = None,
        ai_service: Optional[PydanticAIService] = None,
    ):
        """
        Initialize ticket workflow orchestrator.

        Args:
            db: Database service
            task_queue: Task queue service
            phase_gate: Phase gate service
            event_bus: Optional event bus for publishing events
            ai_service: Optional PydanticAI service for blocker analysis
        """
        self.db = db
        self.task_queue = task_queue
        self.phase_gate = phase_gate
        self.event_bus = event_bus
        self.ai_service = ai_service or PydanticAIService()

    # ---------------------------------------------------------------------
    # State Machine Transitions (REQ-TKT-SM-001, REQ-TKT-SM-002)
    # ---------------------------------------------------------------------

    def transition_status(
        self,
        ticket_id: str,
        to_status: str,
        initiated_by: Optional[str] = None,
        reason: Optional[str] = None,
        force: bool = False,
    ) -> Ticket:
        """
        Transition ticket to new status with validation per REQ-TKT-SM-002.

        Args:
            ticket_id: Ticket ID
            to_status: Target status
            initiated_by: Agent or user ID initiating transition
            reason: Optional reason for transition
            force: Skip validation if True (guardian override)

        Returns:
            Updated ticket

        Raises:
            InvalidTransitionError: If transition is not valid
            TicketBlockedError: If ticket is blocked (unless force=True)
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")

            from_status = ticket.status

            # Validate transition unless forced
            if not force:
                # Check if blocked first (unless transitioning to unblock state)
                # When blocked, can only transition to BLOCKED_TRANSITIONS (unblock states)
                if ticket.is_blocked and to_status not in BLOCKED_TRANSITIONS:
                    raise TicketBlockedError(
                        f"Ticket is blocked (reason: {ticket.blocked_reason}), "
                        f"cannot transition to {to_status}. "
                        f"Must transition to an unblock state: {BLOCKED_TRANSITIONS}"
                    )

                # Validate transition (for blocked tickets, unblock transitions are already validated above)
                if not is_valid_transition(
                    from_status, to_status, is_blocked=ticket.is_blocked
                ):
                    raise InvalidTransitionError(
                        f"Invalid transition from {from_status} to {to_status} "
                        f"(blocked={ticket.is_blocked})"
                    )

            # Update status
            previous_phase_id = ticket.phase_id
            ticket.status = to_status
            ticket.previous_phase_id = previous_phase_id

            # Update phase_id based on status
            if to_status in self.STATUS_TO_PHASE:
                ticket.phase_id = self.STATUS_TO_PHASE[to_status]

            # Clear blocked flag if transitioning from blocked state
            if ticket.is_blocked and to_status in BLOCKED_TRANSITIONS:
                ticket.is_blocked = False
                ticket.blocked_reason = None
                ticket.blocked_at = None

            ticket.updated_at = utc_now()

            # Record phase history
            phase_history = PhaseHistory(
                ticket_id=ticket.id,
                from_phase=previous_phase_id,
                to_phase=ticket.phase_id,
                transition_reason=reason or f"Status transition: {from_status} → {to_status}",
                transitioned_by=initiated_by,
                artifacts=None,
            )
            session.add(phase_history)

            session.commit()
            session.refresh(ticket)
            session.expunge(ticket)

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="ticket.status_transitioned",
                        entity_type="ticket",
                        entity_id=str(ticket.id),
                        payload={
                            "from_status": from_status,
                            "to_status": to_status,
                            "from_phase": previous_phase_id,
                            "to_phase": ticket.phase_id,
                            "initiated_by": initiated_by,
                            "reason": reason,
                        },
                    )
                )

            return ticket

    # ---------------------------------------------------------------------
    # Automatic Progression (REQ-TKT-SM-003)
    # ---------------------------------------------------------------------

    def check_and_progress_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """
        Check if ticket should automatically progress to next phase per REQ-TKT-SM-003.

        Args:
            ticket_id: Ticket ID to check

        Returns:
            Updated ticket if progressed, None if no progression
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return None

            # Skip if blocked or in terminal state
            if ticket.is_blocked or TicketStatus.is_terminal(ticket.status):
                return None

            # Check if phase gate criteria are met
            gate_result = self.phase_gate.check_gate_requirements(
                ticket_id, ticket.phase_id
            )

            if not gate_result["requirements_met"]:
                return None  # Gate criteria not met, cannot progress

            # Determine next status based on current status
            next_status = self._get_next_status(ticket.status)
            if not next_status:
                return None  # No next status available

            # Transition to next status
            session.expunge(ticket)
            return self.transition_status(
                ticket_id,
                next_status,
                initiated_by="ticket-workflow-orchestrator",
                reason="Automatic progression: phase gate criteria met",
            )

    def _get_next_status(self, current_status: str) -> Optional[str]:
        """Get next status in progression chain."""
        progression_map = {
            TicketStatus.BACKLOG.value: TicketStatus.ANALYZING.value,
            TicketStatus.ANALYZING.value: TicketStatus.BUILDING.value,
            TicketStatus.BUILDING.value: TicketStatus.BUILDING_DONE.value,
            TicketStatus.BUILDING_DONE.value: TicketStatus.TESTING.value,
            TicketStatus.TESTING.value: TicketStatus.DONE.value,
        }
        return progression_map.get(current_status)

    # ---------------------------------------------------------------------
    # Regressions (REQ-TKT-SM-004)
    # ---------------------------------------------------------------------

    def regress_ticket(
        self,
        ticket_id: str,
        to_status: str,
        validation_feedback: Optional[str] = None,
        initiated_by: Optional[str] = None,
    ) -> Ticket:
        """
        Regress ticket to previous actionable phase per REQ-TKT-SM-004.

        Args:
            ticket_id: Ticket ID
            to_status: Target status (typically BUILDING for testing regressions)
            validation_feedback: Optional validation feedback
            initiated_by: Agent or user ID initiating regression

        Returns:
            Updated ticket

        Raises:
            InvalidTransitionError: If regression is not valid
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")

            # Validate regression transition
            if not is_valid_transition(ticket.status, to_status, is_blocked=ticket.is_blocked):
                raise InvalidTransitionError(
                    f"Invalid regression from {ticket.status} to {to_status}"
                )

        # Store regression context in ticket context
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")

            current_context = ticket.context or {}
            regression_context = {
                "regressed_from": ticket.status,
                "regressed_to": to_status,
                "validation_feedback": validation_feedback,
                "regressed_at": utc_now().isoformat(),
            }

            if "regressions" not in current_context:
                current_context["regressions"] = []
            current_context["regressions"].append(regression_context)
            
            ticket.context = current_context
            ticket.updated_at = utc_now()
            session.commit()

        # Transition to regressed status
        return self.transition_status(
            ticket_id,
            to_status,
            initiated_by=initiated_by or "ticket-workflow-orchestrator",
            reason=f"Regression: {validation_feedback or 'Fix needed'}",
        )

    # ---------------------------------------------------------------------
    # Blocking Detection (REQ-TKT-BL-001, REQ-TKT-BL-002, REQ-TKT-BL-003)
    # ---------------------------------------------------------------------

    def mark_blocked(
        self,
        ticket_id: str,
        blocker_type: str,
        suggested_remediation: Optional[str] = None,
        initiated_by: Optional[str] = None,
    ) -> Ticket:
        """
        Mark ticket as blocked per REQ-TKT-BL-001.

        Args:
            ticket_id: Ticket ID
            blocker_type: Blocker classification (dependency, waiting_on_clarification, failing_checks, environment)
            suggested_remediation: Optional suggested remediation
            initiated_by: Agent or user ID initiating block

        Returns:
            Updated ticket
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")

            # Skip if already blocked
            if ticket.is_blocked:
                session.commit()
                session.refresh(ticket)
                session.expunge(ticket)
                return ticket

            # Skip if in terminal state
            if TicketStatus.is_terminal(ticket.status):
                session.commit()
                session.refresh(ticket)
                session.expunge(ticket)
                return ticket

            # Mark as blocked
            ticket.is_blocked = True
            ticket.blocked_reason = blocker_type
            ticket.blocked_at = utc_now()
            ticket.updated_at = utc_now()

            session.commit()
            session.refresh(ticket)
            session.expunge(ticket)

            # Create remediation task if possible
            self._create_remediation_task(ticket_id, blocker_type)

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="ticket.blocked",
                        entity_type="ticket",
                        entity_id=str(ticket.id),
                        payload={
                            "blocker_type": blocker_type,
                            "suggested_remediation": suggested_remediation,
                            "status": ticket.status,
                            "phase_id": ticket.phase_id,
                            "initiated_by": initiated_by,
                        },
                    )
                )

            return ticket

    def unblock_ticket(
        self,
        ticket_id: str,
        initiated_by: Optional[str] = None,
    ) -> Ticket:
        """
        Unblock ticket and return to previous phase.

        Args:
            ticket_id: Ticket ID
            initiated_by: Agent or user ID initiating unblock

        Returns:
            Updated ticket
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")

            if not ticket.is_blocked:
                return ticket

            # Clear blocked flag
            old_blocked_reason = ticket.blocked_reason
            ticket.is_blocked = False
            ticket.blocked_reason = None
            ticket.blocked_at = None
            ticket.updated_at = utc_now()

            session.commit()
            session.refresh(ticket)
            session.expunge(ticket)

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="ticket.unblocked",
                        entity_type="ticket",
                        entity_id=str(ticket.id),
                        payload={
                            "previous_blocker": old_blocked_reason,
                            "status": ticket.status,
                            "phase_id": ticket.phase_id,
                            "initiated_by": initiated_by,
                        },
                    )
                )

            return ticket

    def detect_blocking(self) -> List[Dict[str, Any]]:
        """
        Detect tickets that should be marked as blocked per REQ-TKT-BL-001.

        Monitors tickets in non-terminal states and checks if they've exceeded
        the blocking threshold with no task progress.

        Returns:
            List of dicts with ticket_id, should_block, blocker_type
        """
        results = []

        with self.db.get_session() as session:
            # Get tickets in non-terminal states that aren't already blocked
            non_terminal_statuses = [
                TicketStatus.BACKLOG.value,
                TicketStatus.ANALYZING.value,
                TicketStatus.BUILDING.value,
                TicketStatus.BUILDING_DONE.value,
                TicketStatus.TESTING.value,
            ]

            tickets = (
                session.query(Ticket)
                .filter(
                    Ticket.status.in_(non_terminal_statuses),
                    Ticket.is_blocked == False,  # noqa: E712
                )
                .all()
            )

            threshold = timedelta(minutes=self.BLOCKING_THRESHOLD_MINUTES)
            now = utc_now()

            for ticket in tickets:
                # Check if ticket has been in current state longer than threshold
                time_in_state = now - (ticket.updated_at or ticket.created_at)
                if time_in_state < threshold:
                    continue  # Not yet at threshold

                # Check for task progress (any completed tasks in last threshold period)
                has_progress = self._has_task_progress(
                    session, ticket.id, threshold
                )

                if not has_progress:
                    # Classify blocker type
                    # Use sync fallback for now (async version available)
                    blocker_type = self._classify_blocker_sync(session, ticket)
                    results.append({
                        "ticket_id": ticket.id,
                        "should_block": True,
                        "blocker_type": blocker_type,
                        "time_in_state_minutes": time_in_state.total_seconds() / 60,
                    })

        return results

    def _has_task_progress(
        self, session, ticket_id: str, threshold: timedelta
    ) -> bool:
        """Check if ticket has had task progress within threshold period."""
        cutoff = utc_now() - threshold

        # Check for completed tasks
        completed_count = (
            session.query(Task)
            .filter(
                Task.ticket_id == ticket_id,
                Task.status == "completed",
                Task.completed_at >= cutoff,
            )
            .count()
        )

        # Check for task status updates (assigned, running) - use created_at or started_at
        active_count = (
            session.query(Task)
            .filter(
                Task.ticket_id == ticket_id,
                Task.status.in_(["assigned", "running"]),
                Task.created_at >= cutoff,
            )
            .count()
        )

        # Also check for recently started tasks
        started_count = (
            session.query(Task)
            .filter(
                Task.ticket_id == ticket_id,
                Task.started_at.isnot(None),
                Task.started_at >= cutoff,
            )
            .count()
        )

        return completed_count > 0 or active_count > 0 or started_count > 0

    async def _classify_blocker(self, session, ticket: Ticket) -> BlockerAnalysis:
        """
        Classify blocker type using PydanticAI per REQ-TKT-BL-002.

        Args:
            session: Database session
            ticket: Ticket to analyze

        Returns:
            BlockerAnalysis with structured blocker classification and unblocking steps
        """
        # Gather context about the ticket
        failing_tasks = (
            session.query(Task)
            .filter(
                Task.ticket_id == ticket.id,
                Task.status == "failed",
            )
            .all()
        )

        pending_tasks = (
            session.query(Task)
            .filter(
                Task.ticket_id == ticket.id,
                Task.status == "pending",
            )
            .all()
        )

        # Create agent with structured output
        agent = self.ai_service.create_agent(
            output_type=BlockerAnalysis,
            system_prompt=(
                "You are a blocker analysis expert. Analyze tickets to identify why they are blocked. "
                "Classify blocker types (dependency, resource, validation, approval, etc.) and provide "
                "actionable unblocking steps with priority levels (CRITICAL, HIGH, MEDIUM, LOW) and "
                "effort estimates (S, M, L)."
            ),
        )

        # Build prompt with ticket context
        prompt_parts = [
            f"Ticket ID: {ticket.id}",
            f"Title: {ticket.title}",
            f"Description: {ticket.description or 'No description'}",
            f"Status: {ticket.status}",
            f"Phase: {ticket.phase_id}",
        ]

        if failing_tasks:
            prompt_parts.append(f"\nFailing Tasks ({len(failing_tasks)}):")
            for task in failing_tasks[:5]:
                prompt_parts.append(
                    f"- {task.task_type}: {task.error_message or 'No error message'}"
                )

        if pending_tasks:
            prompt_parts.append(f"\nPending Tasks ({len(pending_tasks)}):")
            for task in pending_tasks[:5]:
                prompt_parts.append(f"- {task.task_type}: {task.description or 'No description'}")

        prompt = "\n".join(prompt_parts)
        prompt += "\n\nAnalyze why this ticket is blocked and provide unblocking steps."

        # Run analysis
        result = await agent.run(prompt)
        return result.data

    def _classify_blocker_sync(self, session, ticket: Ticket) -> str:
        """
        Synchronous fallback for blocker classification (rule-based).

        Returns:
            Blocker classification: dependency, waiting_on_clarification, failing_checks, environment
        """
        # Check for failing tasks (failing_checks)
        failing_tasks = (
            session.query(Task)
            .filter(
                Task.ticket_id == ticket.id,
                Task.status == "failed",
            )
            .count()
        )

        if failing_tasks > 0:
            return "failing_checks"

        # Default classification
        return "waiting_on_clarification"

    def _create_remediation_task(
        self, ticket_id: str, blocker_type: str
    ) -> None:
        """
        Create remediation task based on blocker classification per REQ-TKT-BL-003.

        Args:
            ticket_id: Ticket ID
            blocker_type: Blocker classification
        """
        task_descriptions = {
            "dependency": "Resolve dependency",
            "waiting_on_clarification": "Request clarification",
            "failing_checks": "Fix failing checks",
            "environment": "Fix environment",
        }

        description = task_descriptions.get(blocker_type, "Resolve blocker")

        # Create task via TaskQueueService
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return

            try:
                self.task_queue.create_task(
                    ticket_id=ticket_id,
                    phase_id=ticket.phase_id,
                    task_type="remediation",
                    description=description,
                    priority=ticket.priority,
                )
            except Exception:
                # Fail silently - remediation task creation is best effort
                pass

