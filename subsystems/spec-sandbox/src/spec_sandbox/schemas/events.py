"""Event schema for spec sandbox.

Unified event format for all reporters (array, jsonl, http).
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from spec_sandbox.utils import utc_now


class Event(BaseModel):
    """Unified event format for all reporters."""

    event_type: str = Field(..., description="Event type identifier")
    timestamp: datetime = Field(default_factory=utc_now)
    spec_id: str
    phase: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    model_config = {
        "json_encoders": {datetime: lambda v: v.isoformat()},
    }


class EventTypes:
    """Common event type identifiers.

    Event naming convention:
    - Spec lifecycle events use "spec." prefix to match UI expectations
    - Phase events use "spec.phase_" prefix for consistency
    - Execution/monitoring events use "spec." prefix
    - Artifact events use "spec." prefix
    - Agent events use "agent." prefix (handled by backend)
    """

    # Lifecycle
    SPEC_STARTED = "spec.execution_started"
    SPEC_COMPLETED = "spec.execution_completed"
    SPEC_FAILED = "spec.execution_failed"

    # Phase events
    PHASE_STARTED = "spec.phase_started"
    PHASE_COMPLETED = "spec.phase_completed"
    PHASE_FAILED = "spec.phase_failed"
    PHASE_RETRY = "spec.phase_retry"

    # Execution
    HEARTBEAT = "spec.heartbeat"
    PROGRESS = "spec.progress"
    EVAL_RESULT = "spec.eval_result"

    # Artifacts
    ARTIFACT_CREATED = "spec.artifact_created"
    REQUIREMENTS_GENERATED = "spec.requirements_generated"
    DESIGN_GENERATED = "spec.design_generated"
    TASKS_GENERATED = "spec.tasks_generated"

    # Sync phase specific
    SYNC_STARTED = "spec.sync_started"
    SYNC_COMPLETED = "spec.sync_completed"
    TASKS_QUEUED = "spec.tasks_queued"

    # Ticket creation events
    TICKETS_CREATION_STARTED = "spec.tickets_creation_started"
    TICKETS_CREATION_COMPLETED = "spec.tickets_creation_completed"
    TICKET_CREATED = "spec.ticket_created"
    TASK_CREATED = "spec.task_created"
