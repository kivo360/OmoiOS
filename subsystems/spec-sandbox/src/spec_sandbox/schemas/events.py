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
    """Common event type identifiers."""

    # Lifecycle
    SPEC_STARTED = "spec_started"
    SPEC_COMPLETED = "spec_completed"
    SPEC_FAILED = "spec_failed"

    # Phase events
    PHASE_STARTED = "phase_started"
    PHASE_COMPLETED = "phase_completed"
    PHASE_FAILED = "phase_failed"
    PHASE_RETRY = "phase_retry"

    # Execution
    HEARTBEAT = "heartbeat"
    PROGRESS = "progress"
    EVAL_RESULT = "eval_result"

    # Artifacts
    ARTIFACT_CREATED = "artifact_created"
    REQUIREMENTS_GENERATED = "requirements_generated"
    DESIGN_GENERATED = "design_generated"
    TASKS_GENERATED = "tasks_generated"
