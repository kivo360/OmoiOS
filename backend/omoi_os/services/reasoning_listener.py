"""
Reasoning Event Listener Service

Listens to system events and automatically creates reasoning chain events.
This bridges the event bus to the reasoning chain storage for automatic tracking.
"""

import logging
from typing import Any, Optional

from omoi_os.models.reasoning import ReasoningEvent
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent

logger = logging.getLogger(__name__)


def _ensure_serializable(value: Any) -> Any:
    """
    Ensure a value is JSON-serializable.
    Handles Pydantic models, empty sequences, and None values.
    """
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        # Pydantic model - use mode="json" for safe serialization
        return value.model_dump(mode="json")
    if isinstance(value, (list, tuple)):
        # Return empty list for empty sequences
        if not value:
            return []
        return [_ensure_serializable(item) for item in value]
    if isinstance(value, dict):
        # Return empty dict for empty dicts
        if not value:
            return {}
        return {k: _ensure_serializable(v) for k, v in value.items()}
    return value


# Mapping of system event types to reasoning event types
EVENT_TYPE_MAPPING = {
    "TICKET_CREATED": "ticket_created",
    "TICKET_UPDATED": "ticket_created",
    "TASK_ASSIGNED": "task_spawned",
    "TASK_COMPLETED": "code_change",
    "TASK_FAILED": "error",
    "AGENT_DECISION": "agent_decision",
    "BLOCKING_ADDED": "blocking_added",
    "BLOCKING_REMOVED": "blocking_added",
    "CODE_COMMITTED": "code_change",
    "TEST_COMPLETED": "code_change",
    "DISCOVERY": "discovery",
    "ERROR": "error",
    "APPROVAL_REQUESTED": "agent_decision",
    "APPROVAL_GRANTED": "agent_decision",
    "PHASE_TRANSITION": "agent_decision",
}


class ReasoningListenerService:
    """
    Listens to system events and creates corresponding reasoning chain events.

    Usage:
        # Start in a background thread or async task
        listener = ReasoningListenerService(event_bus, db_service)
        listener.start()  # Blocking - runs event loop

        # Or manually process an event
        listener.process_event(system_event)
    """

    def __init__(
        self,
        event_bus: EventBusService,
        db_service: DatabaseService,
    ):
        self.event_bus = event_bus
        self.db = db_service
        self._subscribed = False

    def subscribe_to_events(self) -> None:
        """Subscribe to all relevant system event types."""
        if self._subscribed:
            return

        for event_type in EVENT_TYPE_MAPPING.keys():
            self.event_bus.subscribe(event_type, self._handle_event)
            logger.info(f"Subscribed to event type: {event_type}")

        self._subscribed = True

    def start(self) -> None:
        """Start listening for events (blocking)."""
        self.subscribe_to_events()
        logger.info("ReasoningListenerService started, listening for events...")
        self.event_bus.listen()

    def _handle_event(self, event: SystemEvent) -> None:
        """Handle incoming system event."""
        try:
            self.process_event(event)
        except Exception as e:
            logger.error(f"Error processing event {event.event_type}: {e}")

    def process_event(self, event: SystemEvent) -> Optional[ReasoningEvent]:
        """
        Process a system event and create a reasoning chain event.

        This can be called directly for synchronous event processing,
        or is called automatically when subscribed via start().

        Args:
            event: The system event to process

        Returns:
            The created ReasoningEvent, or None if event was skipped
        """
        reasoning_type = EVENT_TYPE_MAPPING.get(event.event_type)
        if not reasoning_type:
            logger.debug(f"Skipping unmapped event type: {event.event_type}")
            return None

        # Build reasoning event from system event
        title, description, details = self._build_reasoning_data(event)

        # Ensure all complex fields are JSON-serializable
        evidence = self._extract_evidence(event)
        decision = self._extract_decision(event)

        with self.db.get_session() as session:
            reasoning_event = ReasoningEvent(
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                event_type=reasoning_type,
                title=title,
                description=description,
                agent=event.payload.get("agent_id") or event.payload.get("agent"),
                details=details if details else {},
                evidence=evidence if evidence else [],
                decision=decision,
            )

            session.add(reasoning_event)
            session.commit()
            session.refresh(reasoning_event)

            logger.info(
                f"Created reasoning event {reasoning_event.id} "
                f"for {event.entity_type}/{event.entity_id}"
            )

            return reasoning_event

    def _build_reasoning_data(self, event: SystemEvent) -> tuple[str, str, dict]:
        """Build title, description, and details from system event."""
        payload = event.payload
        event_type = event.event_type

        # Default values
        title = event_type.replace("_", " ").title()
        description = f"{event_type} for {event.entity_type} {event.entity_id}"
        details = {}

        # Customize based on event type
        if event_type == "TICKET_CREATED":
            title = "Ticket Created"
            description = payload.get("title", f"Created ticket {event.entity_id}")
            details = {
                "context": payload.get("description"),
                "created_by": payload.get("created_by", "system"),
            }

        elif event_type == "TASK_ASSIGNED":
            title = "Task Assigned"
            agent = payload.get("agent_id", "unknown")
            description = f"Task assigned to agent {agent}"
            details = {
                "reasoning": payload.get("reason", "Assigned based on availability"),
                "tasks": [event.entity_id],
            }

        elif event_type == "TASK_COMPLETED":
            title = "Task Completed"
            description = payload.get("summary", f"Task {event.entity_id} completed")
            details = {
                "task": event.entity_id,
                "lines_added": payload.get("lines_added", 0),
                "lines_removed": payload.get("lines_removed", 0),
                "files_changed": payload.get("files_changed", 0),
                "commit": payload.get("commit_hash"),
            }

        elif event_type == "TASK_FAILED":
            title = "Task Failed"
            description = payload.get("error", f"Task {event.entity_id} failed")
            details = {
                "error_type": payload.get("error_type", "unknown"),
                "stack_trace": payload.get("stack_trace"),
                "context": payload.get("context"),
            }

        elif event_type == "AGENT_DECISION":
            title = payload.get("decision_title", "Agent Decision")
            description = payload.get("description", "Agent made a decision")
            details = {
                "reasoning": payload.get("reasoning"),
                "confidence": payload.get("confidence"),
                "context": payload.get("context"),
                "alternatives": payload.get("alternatives", []),
            }

        elif event_type == "BLOCKING_ADDED":
            title = "Blocking Dependency Added"
            blocked = payload.get("blocked_by", "unknown")
            description = f"Blocked by {blocked}"
            details = {
                "blocked_ticket": blocked,
                "blocked_title": payload.get("blocked_title"),
                "reason": payload.get("reason"),
            }

        elif event_type == "CODE_COMMITTED":
            title = "Code Committed"
            commit = payload.get("commit_hash", "unknown")[:7]
            description = payload.get("message", f"Committed {commit}")
            details = {
                "commit": payload.get("commit_hash"),
                "lines_added": payload.get("lines_added", 0),
                "lines_removed": payload.get("lines_removed", 0),
                "files_changed": payload.get("files_changed", 0),
            }

        elif event_type == "DISCOVERY":
            title = payload.get("title", "Discovery Made")
            description = payload.get(
                "description", "New discovery during implementation"
            )
            details = {
                "discovery_type": payload.get("discovery_type", "general"),
                "impact": payload.get("impact"),
                "action": payload.get("action"),
                "evidence": payload.get("evidence"),
            }

        elif event_type == "TEST_COMPLETED":
            passing = payload.get("tests_passing", 0)
            total = payload.get("tests_total", 0)
            title = "Tests Completed"
            description = f"Tests completed: {passing}/{total} passing"
            details = {
                "tests_passing": passing,
                "tests_total": total,
                "task": payload.get("task_id"),
            }

        elif event_type == "PHASE_TRANSITION":
            from_phase = payload.get("from_phase", "unknown")
            to_phase = payload.get("to_phase", "unknown")
            title = "Phase Transition"
            description = f"Transitioned from {from_phase} to {to_phase}"
            details = {
                "reasoning": payload.get("reason"),
                "context": f"Phase changed: {from_phase} → {to_phase}",
            }

        elif event_type in ("APPROVAL_REQUESTED", "APPROVAL_GRANTED"):
            action = "requested" if event_type == "APPROVAL_REQUESTED" else "granted"
            title = f"Approval {action.title()}"
            description = payload.get("description", f"Approval {action}")
            details = {
                "reasoning": payload.get("reason"),
                "context": payload.get("context"),
            }

        # Include any extra payload data not explicitly mapped
        for key, value in payload.items():
            if key not in details and key not in ("title", "description"):
                details[key] = value

        return title, description, details

    def _extract_evidence(self, event: SystemEvent) -> list[dict]:
        """Extract evidence items from event payload."""
        evidence = []
        payload = event.payload

        # Check for explicit evidence in payload
        if "evidence" in payload:
            if isinstance(payload["evidence"], list):
                evidence.extend(payload["evidence"])
            elif isinstance(payload["evidence"], str):
                evidence.append({"type": "log", "content": payload["evidence"]})

        # Extract test results as evidence
        if "tests_passing" in payload and "tests_total" in payload:
            evidence.append(
                {
                    "type": "test",
                    "content": f"{payload['tests_passing']}/{payload['tests_total']} tests passing",
                }
            )

        # Extract coverage as evidence
        if "coverage" in payload:
            evidence.append(
                {
                    "type": "coverage",
                    "content": f"{payload['coverage']}% code coverage",
                }
            )

        # Extract error as evidence
        if "error" in payload:
            evidence.append(
                {
                    "type": "error",
                    "content": payload["error"],
                }
            )

        return evidence

    def _extract_decision(self, event: SystemEvent) -> Optional[dict]:
        """Extract decision from event payload if present."""
        payload = event.payload

        # Check for explicit decision
        if "decision" in payload and isinstance(payload["decision"], dict):
            return payload["decision"]

        # Build decision for certain event types
        if event.event_type == "AGENT_DECISION":
            return {
                "type": payload.get("decision_type", "proceed"),
                "action": payload.get("action", "Continue"),
                "reasoning": payload.get("reasoning", "Based on analysis"),
            }

        if event.event_type == "TASK_COMPLETED":
            return {
                "type": "complete",
                "action": "Task completed successfully",
                "reasoning": payload.get("summary", "All acceptance criteria met"),
            }

        if event.event_type == "TASK_FAILED":
            return {
                "type": "block",
                "action": "Investigate failure",
                "reasoning": payload.get("error", "Task failed - investigation needed"),
            }

        return None


# Convenience function for direct event processing without listener
def log_reasoning_event(
    db: DatabaseService,
    entity_type: str,
    entity_id: str,
    event_type: str,
    title: str,
    description: str,
    agent: Optional[str] = None,
    details: Optional[dict] = None,
    evidence: Optional[list] = None,
    decision: Optional[dict] = None,
) -> ReasoningEvent:
    """
    Directly log a reasoning event without going through the event bus.

    Useful for adding events from routes or services that don't use the event bus.

    Example:
        from omoi_os.services.reasoning_listener import log_reasoning_event

        log_reasoning_event(
            db=db,
            entity_type="ticket",
            entity_id="TICKET-123",
            event_type="agent_decision",
            title="Implementation Approach Selected",
            description="Chose incremental approach for safer deployment",
            agent="worker-1",
            details={"reasoning": "Minimizes risk"},
            decision={"type": "proceed", "action": "Start implementation", "reasoning": "Low risk"}
        )
    """
    # Ensure all complex fields are JSON-serializable
    safe_details = _ensure_serializable(details) if details else {}
    safe_evidence = _ensure_serializable(evidence) if evidence else []
    safe_decision = _ensure_serializable(decision) if decision else None

    with db.get_session() as session:
        event = ReasoningEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            title=title,
            description=description,
            agent=agent,
            details=safe_details,
            evidence=safe_evidence,
            decision=safe_decision,
        )
        session.add(event)
        session.commit()
        session.refresh(event)
        return event
