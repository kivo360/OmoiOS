"""
Base evaluator classes for spec-driven development phases.

Evaluators validate phase outputs before proceeding to the next phase.
They provide structured feedback that can be used for retry prompts.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalResult:
    """Result of evaluating phase output."""

    passed: bool
    score: float  # 0.0 to 1.0
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, bool] = field(default_factory=dict)
    feedback_for_retry: str = ""

    def __post_init__(self):
        """Generate feedback for retry if not provided."""
        if not self.feedback_for_retry and self.failures:
            self.feedback_for_retry = (
                f"Your output failed {len(self.failures)} validation checks:\n"
                + "\n".join(f"- {f}" for f in self.failures)
            )


class BaseEvaluator(ABC):
    """
    Abstract base class for phase evaluators.

    Evaluators validate the output of each phase before the state machine
    proceeds to the next phase. If validation fails, the feedback is used
    to construct a retry prompt.
    """

    # Minimum score required to pass (default 0.7 = 70%)
    min_score: float = 0.7

    @abstractmethod
    def evaluate(self, data: Any) -> EvalResult:
        """
        Evaluate phase output.

        Args:
            data: The output from the phase (dict, list, or Pydantic model)

        Returns:
            EvalResult with pass/fail status, score, and failure details
        """
        pass

    def _make_result(self, checks: list[tuple[str, bool]]) -> EvalResult:
        """
        Helper to build EvalResult from list of (check_name, passed) tuples.

        Args:
            checks: List of tuples like [("has_requirements", True), ("ears_format", False)]

        Returns:
            EvalResult with computed pass/score/failures/details
        """
        if not checks:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["no_checks_performed"],
                details={},
            )

        passed_count = sum(1 for _, passed in checks if passed)
        total_count = len(checks)
        score = passed_count / total_count

        failures = [name for name, passed in checks if not passed]
        details = {name: passed for name, passed in checks}

        # Generate readable failure messages
        failure_messages = []
        for name in failures:
            readable = name.replace("_", " ").capitalize()
            failure_messages.append(f"{readable} check failed")

        return EvalResult(
            passed=score >= self.min_score and len(failures) == 0,
            score=score,
            failures=failure_messages,
            details=details,
        )

    def _validate_required_fields(
        self, data: dict, required: list[str]
    ) -> list[tuple[str, bool]]:
        """
        Validate that required fields exist and are non-empty.

        Args:
            data: Dictionary to validate
            required: List of required field names

        Returns:
            List of (field_name, is_valid) tuples
        """
        checks = []
        for field_name in required:
            value = data.get(field_name)
            is_valid = value is not None and value != "" and value != []
            checks.append((f"has_{field_name}", is_valid))
        return checks

    def _validate_list_not_empty(
        self, data: dict, field_name: str, min_count: int = 1
    ) -> tuple[str, bool]:
        """Validate that a list field has at least min_count items."""
        value = data.get(field_name, [])
        is_valid = isinstance(value, list) and len(value) >= min_count
        return (f"{field_name}_has_items", is_valid)
