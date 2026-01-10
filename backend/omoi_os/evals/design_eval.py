"""
Evaluator for the DESIGN phase output.

Validates that technical design is complete and implementable.
"""

from typing import Any

from .base import BaseEvaluator, EvalResult


class DesignEvaluator(BaseEvaluator):
    """
    Evaluates generated design for completeness.

    Design should include:
    - Architecture overview
    - Data models with fields
    - API endpoints with methods and paths
    - Error handling considerations
    """

    # Valid HTTP methods
    VALID_METHODS = frozenset([
        "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"
    ])

    def evaluate(self, design: Any) -> EvalResult:
        """
        Evaluate generated design.

        Args:
            design: Design dict with architecture, data_model/data_models,
                   and api_endpoints fields

        Returns:
            EvalResult indicating if design passes quality gates
        """
        if not design:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["No design provided"],
                details={"no_design": False},
            )

        if not isinstance(design, dict):
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["Invalid design format"],
                details={"valid_format": False},
            )

        checks = []

        # Check 1: Has architecture description
        architecture = design.get("architecture") or design.get("architecture_overview", "")
        has_arch = bool(architecture)
        checks.append(("has_architecture", has_arch))

        # Check 2: Architecture is substantive (not just a few words)
        arch_substantive = len(str(architecture)) > 100 if architecture else False
        checks.append(("architecture_substantive", arch_substantive))

        # Check 3: Has data model
        data_model = design.get("data_model") or design.get("data_models", [])
        has_data = bool(data_model)
        checks.append(("has_data_model", has_data))

        # Check 4: Data models have structure
        if isinstance(data_model, list) and data_model:
            models_have_fields = all(
                self._model_has_fields(m) for m in data_model
            )
        elif isinstance(data_model, dict):
            models_have_fields = bool(data_model)
        elif isinstance(data_model, str) and len(data_model) > 50:
            # Markdown/Mermaid format
            models_have_fields = True
        else:
            models_have_fields = False
        checks.append(("data_models_complete", models_have_fields))

        # Check 5: Has API endpoints
        endpoints = design.get("api_endpoints", [])
        has_api = isinstance(endpoints, list) and len(endpoints) > 0
        checks.append(("has_api_spec", has_api))

        # Check 6: Endpoints have required fields (method, path, description)
        if has_api:
            endpoints_complete = all(
                self._endpoint_is_complete(e) for e in endpoints
            )
        else:
            endpoints_complete = False
        checks.append(("endpoints_complete", endpoints_complete))

        # Check 7: API methods are valid
        if has_api:
            methods_valid = all(
                self._method_is_valid(e) for e in endpoints
            )
        else:
            methods_valid = True  # No endpoints, no invalid methods
        checks.append(("valid_methods", methods_valid))

        # Check 8: Has error handling strategy
        error_handling = design.get("error_handling", "")
        has_error_handling = bool(error_handling) and len(str(error_handling)) > 20
        # This is optional, just a warning
        if has_error_handling:
            checks.append(("has_error_handling", True))

        # Check 9: Components are listed
        components = design.get("components", [])
        has_components = isinstance(components, list) and len(components) > 0
        if has_components:
            checks.append(("has_components", True))

        result = self._make_result(checks)

        # Add warnings for optional but recommended fields
        if not has_error_handling:
            result.warnings.append(
                "No error handling strategy specified. Consider adding error handling considerations."
            )

        if not design.get("security_considerations"):
            result.warnings.append(
                "No security considerations specified. Consider adding auth/validation notes."
            )

        if not design.get("testing_strategy"):
            result.warnings.append(
                "No testing strategy specified. Consider adding testing approach."
            )

        # Specific feedback for common failures
        if not arch_substantive:
            result.feedback_for_retry = (
                "Architecture description is too brief. Please provide a detailed "
                "architecture overview (at least 100 characters) explaining how "
                "components interact and fit with existing code."
            )

        if not endpoints_complete and has_api:
            if result.feedback_for_retry:
                result.feedback_for_retry += "\n\n"
            else:
                result.feedback_for_retry = ""
            result.feedback_for_retry += (
                "API endpoints are incomplete. Each endpoint must have: "
                "method (GET/POST/PUT/PATCH/DELETE), path (/api/v1/...), "
                "and description."
            )

        return result

    def _model_has_fields(self, model: Any) -> bool:
        """Check if a data model has fields defined."""
        if not isinstance(model, dict):
            return False
        # Check for name and some field definition
        has_name = bool(model.get("name"))
        has_fields = bool(model.get("fields")) or bool(model.get("columns"))
        return has_name and has_fields

    def _endpoint_is_complete(self, endpoint: Any) -> bool:
        """Check if an endpoint has required fields."""
        if not isinstance(endpoint, dict):
            return False
        return all([
            endpoint.get("method"),
            endpoint.get("path"),
            endpoint.get("description"),
        ])

    def _method_is_valid(self, endpoint: Any) -> bool:
        """Check if endpoint method is valid HTTP method."""
        if not isinstance(endpoint, dict):
            return True
        method = endpoint.get("method", "")
        return method.upper() in self.VALID_METHODS
