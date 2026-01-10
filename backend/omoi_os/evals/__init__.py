"""
Evaluators for spec-driven development state machine.

Each phase of the spec generation workflow has an evaluator that validates
the output before proceeding to the next phase. Evaluators provide:

1. Pass/fail status based on quality gates
2. Detailed scores for each check
3. Feedback for retry prompts when validation fails

Usage:
    from omoi_os.evals import (
        ExplorationEvaluator,
        RequirementEvaluator,
        DesignEvaluator,
        TaskEvaluator,
    )

    evaluator = RequirementEvaluator()
    result = evaluator.evaluate(requirements_data)

    if result.passed:
        # Proceed to next phase
        pass
    else:
        # Use result.feedback_for_retry in retry prompt
        pass
"""

from .base import BaseEvaluator, EvalResult
from .design_eval import DesignEvaluator
from .exploration_eval import ExplorationEvaluator
from .requirement_eval import RequirementEvaluator
from .task_eval import TaskEvaluator

__all__ = [
    # Base classes
    "BaseEvaluator",
    "EvalResult",
    # Evaluators
    "ExplorationEvaluator",
    "RequirementEvaluator",
    "DesignEvaluator",
    "TaskEvaluator",
]
