"""Evaluators for spec phases.

Each evaluator scores the output of a phase to determine
if it meets quality thresholds.
"""

from spec_sandbox.evaluators.base import BaseEvaluator, EvalResult

__all__ = ["BaseEvaluator", "EvalResult"]
