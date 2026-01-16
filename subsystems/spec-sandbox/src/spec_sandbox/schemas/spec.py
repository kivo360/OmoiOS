"""Spec-related schemas."""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SpecPhase(str, Enum):
    """Spec execution phases."""

    EXPLORE = "explore"
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
