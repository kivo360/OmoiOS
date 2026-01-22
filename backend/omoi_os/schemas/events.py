"""Canonical event type definitions for OmoiOS.

This module defines the authoritative event types used across the system.
Events are organized into categories based on their stability and purpose:

1. STABLE - Lifecycle Events (Non-Work)
   These events represent fundamental lifecycle signals that don't indicate
   actual work progress. They're stable because they represent universal
   concepts: heartbeats, errors, startup, shutdown.

2. STABLE - Phase/Progression Events
   These events represent state machine transitions and workflow progression.
   They're stable because they map to the core workflow model (EXPLORE →
   REQUIREMENTS → DESIGN → TASKS → SYNC).

3. EVOLVING - Work Events
   These events indicate actual work being done. They may change as we add
   new capabilities, tools, or execution patterns. The idle monitor uses
   an inverted approach: anything NOT in the non-work set is considered work.

Usage:
    from omoi_os.schemas.events import (
        NON_WORK_EVENTS,
        PHASE_PROGRESSION_EVENTS,
        AgentEventTypes,
        SpecEventTypes,
    )

    # Check if an event indicates work
    is_work = event_type not in NON_WORK_EVENTS

    # Check if an event indicates phase progression
    is_progression = event_type in PHASE_PROGRESSION_EVENTS
"""

from typing import FrozenSet, Set


# =============================================================================
# AGENT EVENT TYPES
# =============================================================================


class AgentEventTypes:
    """Event types emitted by agent workers (claude_sandbox_worker).

    These follow the pattern: agent.{action}
    """

    # Lifecycle (stable - don't indicate work)
    STARTED = "agent.started"
    SHUTDOWN = "agent.shutdown"
    HEARTBEAT = "agent.heartbeat"

    # Status signals (stable - don't indicate forward progress)
    WAITING = "agent.waiting"
    INTERRUPTED = "agent.interrupted"

    # Errors (stable - failures don't indicate progress)
    ERROR = "agent.error"
    STREAM_ERROR = "agent.stream_error"

    # Work events (evolving - these indicate actual work)
    THINKING = "agent.thinking"
    TOOL_USE = "agent.tool_use"
    TOOL_RESULT = "agent.tool_result"
    TEXT_OUTPUT = "agent.text_output"
    RESPONSE = "agent.response"
    COMPLETED = "agent.completed"

    # Result events (evolving)
    RESULT = "agent.result"


class SpecEventTypes:
    """Event types emitted by spec sandbox execution.

    These follow the pattern: spec.{action}
    Mirror of spec_sandbox.schemas.events.EventTypes for backend use.
    """

    # Lifecycle (stable)
    EXECUTION_STARTED = "spec.execution_started"
    EXECUTION_COMPLETED = "spec.execution_completed"
    EXECUTION_FAILED = "spec.execution_failed"
    HEARTBEAT = "spec.heartbeat"

    # Phase events (stable - core workflow model)
    PHASE_STARTED = "spec.phase_started"
    PHASE_COMPLETED = "spec.phase_completed"
    PHASE_FAILED = "spec.phase_failed"
    PHASE_RETRY = "spec.phase_retry"

    # Progress events (evolving - indicate work)
    PROGRESS = "spec.progress"
    EVAL_RESULT = "spec.eval_result"

    # Artifact events (evolving - indicate work)
    ARTIFACT_CREATED = "spec.artifact_created"
    REQUIREMENTS_GENERATED = "spec.requirements_generated"
    DESIGN_GENERATED = "spec.design_generated"
    TASKS_GENERATED = "spec.tasks_generated"

    # Sync phase (evolving)
    SYNC_STARTED = "spec.sync_started"
    SYNC_COMPLETED = "spec.sync_completed"
    TASKS_QUEUED = "spec.tasks_queued"

    # Ticket/task CRUD (evolving)
    TICKETS_CREATION_STARTED = "spec.tickets_creation_started"
    TICKETS_CREATION_COMPLETED = "spec.tickets_creation_completed"
    TICKET_CREATED = "spec.ticket_created"
    TICKET_UPDATED = "spec.ticket_updated"
    TASK_CREATED = "spec.task_created"
    TASK_UPDATED = "spec.task_updated"

    # Requirements/design sync (evolving)
    REQUIREMENTS_SYNC_STARTED = "spec.requirements_sync_started"
    REQUIREMENTS_SYNC_COMPLETED = "spec.requirements_sync_completed"
    REQUIREMENT_CREATED = "spec.requirement_created"
    REQUIREMENT_UPDATED = "spec.requirement_updated"
    DESIGN_SYNC_STARTED = "spec.design_sync_started"
    DESIGN_SYNC_COMPLETED = "spec.design_sync_completed"
    DESIGN_UPDATED = "spec.design_updated"


class IterationEventTypes:
    """Event types for continuous/iteration mode execution.

    These follow the pattern: iteration.{action} or continuous.{action}
    """

    # Iteration lifecycle
    STARTED = "iteration.started"
    COMPLETED = "iteration.completed"
    FAILED = "iteration.failed"

    # Continuous mode
    CONTINUOUS_STARTED = "continuous.started"
    CONTINUOUS_COMPLETED = "continuous.completed"
    CONTINUOUS_STOPPED = "continuous.stopped"


# =============================================================================
# STABLE EVENT SETS (Rarely change)
# =============================================================================


# Events that do NOT indicate actual work progress.
# Used by idle_sandbox_monitor to detect inactive sandboxes.
#
# Design principle: Use a blocklist (non-work) rather than allowlist (work)
# so that NEW event types automatically count as work (fail-safe).
NON_WORK_EVENTS: FrozenSet[str] = frozenset({
    # Heartbeats - just keepalive signals, not actual work
    AgentEventTypes.HEARTBEAT,
    SpecEventTypes.HEARTBEAT,

    # Started events - initialization, not actual work yet
    AgentEventTypes.STARTED,

    # Error events - failures don't indicate forward progress
    AgentEventTypes.ERROR,
    AgentEventTypes.STREAM_ERROR,
    SpecEventTypes.PHASE_FAILED,
    SpecEventTypes.EXECUTION_FAILED,
    IterationEventTypes.FAILED,

    # Waiting/idle states - ready but not actively working
    AgentEventTypes.WAITING,

    # Shutdown events - cleanup, not productive work
    AgentEventTypes.SHUTDOWN,

    # Interrupted events - work was stopped
    AgentEventTypes.INTERRUPTED,
})


# Events that indicate phase/state progression in a workflow.
# Useful for tracking workflow advancement regardless of specific work done.
PHASE_PROGRESSION_EVENTS: FrozenSet[str] = frozenset({
    # Spec phase transitions
    SpecEventTypes.PHASE_STARTED,
    SpecEventTypes.PHASE_COMPLETED,

    # Spec lifecycle milestones
    SpecEventTypes.EXECUTION_STARTED,
    SpecEventTypes.EXECUTION_COMPLETED,

    # Sync phase markers
    SpecEventTypes.SYNC_STARTED,
    SpecEventTypes.SYNC_COMPLETED,

    # Artifact generation milestones
    SpecEventTypes.REQUIREMENTS_GENERATED,
    SpecEventTypes.DESIGN_GENERATED,
    SpecEventTypes.TASKS_GENERATED,

    # Iteration/continuous mode
    IterationEventTypes.STARTED,
    IterationEventTypes.COMPLETED,
    IterationEventTypes.CONTINUOUS_STARTED,
    IterationEventTypes.CONTINUOUS_COMPLETED,
})


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def is_work_event(event_type: str) -> bool:
    """Check if an event type indicates actual work progress.

    Uses inverted logic: anything NOT in NON_WORK_EVENTS is work.
    This means new event types automatically count as work (fail-safe).

    Args:
        event_type: The event type string to check

    Returns:
        True if the event indicates work, False otherwise
    """
    return event_type not in NON_WORK_EVENTS


def is_phase_progression(event_type: str) -> bool:
    """Check if an event type indicates workflow phase progression.

    Args:
        event_type: The event type string to check

    Returns:
        True if the event indicates phase/state progression
    """
    return event_type in PHASE_PROGRESSION_EVENTS


def get_event_category(event_type: str) -> str:
    """Get the category of an event type.

    Args:
        event_type: The event type string

    Returns:
        One of: "agent", "spec", "iteration", "continuous", "unknown"
    """
    if event_type.startswith("agent."):
        return "agent"
    elif event_type.startswith("spec."):
        return "spec"
    elif event_type.startswith("iteration."):
        return "iteration"
    elif event_type.startswith("continuous."):
        return "continuous"
    return "unknown"


# =============================================================================
# EXPORTS
# =============================================================================


__all__ = [
    # Event type classes
    "AgentEventTypes",
    "SpecEventTypes",
    "IterationEventTypes",
    # Stable event sets
    "NON_WORK_EVENTS",
    "PHASE_PROGRESSION_EVENTS",
    # Helper functions
    "is_work_event",
    "is_phase_progression",
    "get_event_category",
]
