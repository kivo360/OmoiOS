"""Evaluators for spec phases.

Each evaluator scores the output of a phase to determine
if it meets quality thresholds.

Enhanced with validation patterns from the spec-driven-dev skill scripts:
- Normative language detection for requirements (SHALL, SHOULD, MAY, MUST)
- EARS trigger detection (WHEN, WHILE, WHERE, IF)
- Circular dependency detection using DFS
- ID format validation (REQ-XXX-YYY-NNN, TASK-NNN, etc.)
- Traceability statistics
"""

from spec_sandbox.evaluators.base import BaseEvaluator, EvalResult
from spec_sandbox.evaluators.markdown import (
    MarkdownOutputEvaluator,
    validate_markdown_directory,
)
from spec_sandbox.evaluators.phases import (
    ExploreEvaluator,
    RequirementsEvaluator,
    DesignEvaluator,
    TasksEvaluator,
    SyncEvaluator,
    get_evaluator,
)
from spec_sandbox.evaluators.validation import (
    ValidationError,
    ValidationResult,
    validate_id_format,
    validate_requirement_text,
    validate_task_references,
    validate_requirements_addressed,
    validate_component_responsibilities,
    detect_normative_language,
    detect_circular_dependencies,
    calculate_traceability_stats,
    ID_PATTERNS,
    RELAXED_ID_PATTERNS,
    NORMATIVE_KEYWORDS,
    EARS_TRIGGERS,
)

__all__ = [
    # Base classes
    "BaseEvaluator",
    "EvalResult",
    # Phase evaluators
    "ExploreEvaluator",
    "RequirementsEvaluator",
    "DesignEvaluator",
    "TasksEvaluator",
    "SyncEvaluator",
    "get_evaluator",
    # Markdown evaluator
    "MarkdownOutputEvaluator",
    "validate_markdown_directory",
    # Validation classes
    "ValidationError",
    "ValidationResult",
    # Validation functions
    "validate_id_format",
    "validate_requirement_text",
    "validate_task_references",
    "validate_requirements_addressed",
    "validate_component_responsibilities",
    "detect_normative_language",
    "detect_circular_dependencies",
    "calculate_traceability_stats",
    # Validation constants
    "ID_PATTERNS",
    "RELAXED_ID_PATTERNS",
    "NORMATIVE_KEYWORDS",
    "EARS_TRIGGERS",
]
