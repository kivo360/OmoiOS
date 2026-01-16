"""Base evaluator for spec phases."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EvalResult(BaseModel):
    """Result of an evaluation."""

    score: float = Field(..., ge=0.0, le=1.0, description="Evaluation score 0-1")
    passed: bool = Field(description="Whether evaluation passed threshold")
    feedback: Optional[str] = Field(default=None, description="Feedback for improvement")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed scores")


class BaseEvaluator(ABC):
    """Base class for phase evaluators."""

    # Default passing threshold
    threshold: float = 0.7

    @abstractmethod
    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate phase output.

        Args:
            output: The output from the phase execution
            context: Accumulated context from previous phases

        Returns:
            EvalResult with score and pass/fail status
        """
        pass

    def _create_result(
        self,
        score: float,
        feedback: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> EvalResult:
        """Helper to create EvalResult."""
        return EvalResult(
            score=score,
            passed=score >= self.threshold,
            feedback=feedback,
            details=details or {},
        )
