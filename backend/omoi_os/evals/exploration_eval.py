"""
Evaluator for the EXPLORE phase output.

Validates that codebase exploration produced sufficient context
for subsequent phases to generate accurate, codebase-aware specs.
"""

from typing import Any

from .base import BaseEvaluator, EvalResult


class ExplorationEvaluator(BaseEvaluator):
    """
    Evaluates exploration context for completeness.

    The exploration phase should discover:
    - Project structure (models, routes, services directories)
    - Existing models and their fields
    - Existing routes and patterns
    - Conventions (naming, ID formats, testing)
    - Technology stack

    Passing exploration context leads to better requirements and design.
    """

    def evaluate(self, data: Any) -> EvalResult:
        """
        Evaluate exploration context.

        Args:
            data: Exploration context dict with project structure,
                  existing models, routes, and conventions

        Returns:
            EvalResult indicating if exploration was thorough enough
        """
        if not data or not isinstance(data, dict):
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["No exploration data provided"],
                details={"has_data": False},
            )

        checks = []

        # Check 1: Has project type
        has_project_type = bool(data.get("project_type"))
        checks.append(("has_project_type", has_project_type))

        # Check 2: Has structure info
        structure = data.get("structure", {})
        has_structure = isinstance(structure, dict) and len(structure) > 0
        checks.append(("has_structure", has_structure))

        # Check 3: Has at least some existing models discovered
        existing_models = data.get("existing_models", [])
        has_models = isinstance(existing_models, list) and len(existing_models) > 0
        checks.append(("discovered_models", has_models))

        # Check 4: Models have required fields (name, file)
        models_complete = True
        if has_models:
            for model in existing_models:
                if not isinstance(model, dict):
                    models_complete = False
                    break
                if not model.get("name") or not model.get("file"):
                    models_complete = False
                    break
        else:
            models_complete = False
        checks.append(("models_complete", models_complete))

        # Check 5: Has conventions discovered
        conventions = data.get("conventions", {})
        has_conventions = isinstance(conventions, dict) and len(conventions) > 0
        checks.append(("discovered_conventions", has_conventions))

        # Check 6: Has feature-related discoveries (if exploring for a specific feature)
        related = data.get("related_to_feature", {})
        # This is optional - don't fail if not present
        has_related = isinstance(related, dict) and len(related) > 0
        # Give partial credit for related discovery
        if has_related:
            checks.append(("feature_related_context", True))

        # Check 7: Has explored files list (proves actual exploration happened)
        explored_files = data.get("explored_files", [])
        has_explored_files = isinstance(explored_files, list) and len(explored_files) > 0
        checks.append(("explored_files", has_explored_files))

        # Check 8: Has technology stack
        tech_stack = data.get("tech_stack", data.get("technology_stack", {}))
        has_tech_stack = bool(tech_stack)
        checks.append(("has_tech_stack", has_tech_stack))

        result = self._make_result(checks)

        # Add specific warnings for missing optional context
        if not has_related:
            result.warnings.append(
                "No feature-related context discovered. "
                "Requirements may not integrate well with existing code."
            )

        if not has_explored_files:
            result.warnings.append(
                "No explored files recorded. Cannot verify exploration depth."
            )

        return result
