"""Spec-related schemas."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SpecPhase(str, Enum):
    """Spec execution phases.

    Phase order: EXPLORE → PRD → REQUIREMENTS → DESIGN → TASKS → SYNC

    - EXPLORE: Discover codebase structure, patterns, and context
    - PRD: Define product vision, goals, success metrics, and user stories
    - REQUIREMENTS: Translate PRD into formal EARS-format requirements
    - DESIGN: Create technical architecture and API specifications
    - TASKS: Break design into implementable tickets and tasks
    - SYNC: Validate traceability and coverage across all phases
    """

    EXPLORE = "explore"
    PRD = "prd"
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    TASKS = "tasks"
    SYNC = "sync"


class PhaseResult(BaseModel):
    """Result of a phase execution."""

    phase: SpecPhase
    success: bool
    eval_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    duration_seconds: Optional[float] = None
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0

    @property
    def passed(self) -> bool:
        """Check if phase passed evaluation threshold."""
        if not self.success:
            return False
        if self.eval_score is None:
            return True
        return self.eval_score >= 0.7  # Default threshold
