"""
Evaluator for the REQUIREMENTS phase output.

Validates that requirements follow EARS format and are testable.
"""

from typing import Any

from .base import BaseEvaluator, EvalResult


class RequirementEvaluator(BaseEvaluator):
    """
    Evaluates generated requirements for quality and format.

    Requirements should:
    - Follow EARS format (WHEN [condition], THE SYSTEM SHALL [action])
    - Have clear, testable acceptance criteria
    - Not have duplicate titles
    - Reference integration points with existing code
    """

    # Action words that indicate testable criteria
    TESTABLE_WORDS = frozenset([
        "should", "must", "will", "shall",
        "returns", "displays", "shows", "creates",
        "updates", "deletes", "modifies", "validates",
        "within", "less than", "greater than", "at least",
        "exactly", "between", "responds", "accepts",
        "rejects", "stores", "retrieves", "sends",
        "receives", "generates", "triggers", "logs",
    ])

    def evaluate(self, requirements: Any) -> EvalResult:
        """
        Evaluate generated requirements.

        Args:
            requirements: List of requirement dicts with title, condition,
                         action, and criteria fields

        Returns:
            EvalResult indicating if requirements pass quality gates
        """
        if not requirements:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["No requirements provided"],
                details={"no_requirements": False},
            )

        # Handle both list and dict (RequirementsOutput) formats
        if isinstance(requirements, dict):
            req_list = requirements.get("requirements", [])
        elif isinstance(requirements, list):
            req_list = requirements
        else:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["Invalid requirements format"],
                details={"valid_format": False},
            )

        if not req_list:
            return EvalResult(
                passed=False,
                score=0.0,
                failures=["No requirements in list"],
                details={"has_requirements": False},
            )

        checks = []

        # Check 1: Has requirements
        has_requirements = len(req_list) >= 1
        checks.append(("has_requirements", has_requirements))

        # Check 2: EARS format (WHEN condition exists)
        ears_valid = all(
            self._has_ears_condition(req.get("condition", ""))
            for req in req_list
        )
        checks.append(("ears_format", ears_valid))

        # Check 3: Has action clause
        has_actions = all(
            bool(req.get("action"))
            for req in req_list
        )
        checks.append(("has_actions", has_actions))

        # Check 4: Has acceptance criteria (at least 2 per requirement)
        has_criteria = all(
            len(self._get_criteria(req)) >= 2
            for req in req_list
        )
        checks.append(("has_criteria", has_criteria))

        # Check 5: No duplicate titles
        titles = [req.get("title", "") for req in req_list]
        no_duplicates = len(set(titles)) == len(titles) and "" not in titles
        checks.append(("no_duplicates", no_duplicates))

        # Check 6: All have titles and actions
        complete = all(
            req.get("title") and req.get("action")
            for req in req_list
        )
        checks.append(("complete_fields", complete))

        # Check 7: Criteria are testable (have action words)
        all_criteria = []
        for req in req_list:
            all_criteria.extend(self._get_criteria(req))

        if all_criteria:
            testable_count = sum(
                1 for c in all_criteria
                if self._is_testable(c)
            )
            criteria_testable = testable_count >= len(all_criteria) * 0.7
        else:
            criteria_testable = False
        checks.append(("testable_criteria", criteria_testable))

        # Check 8: Has priority assigned
        has_priority = all(
            req.get("priority") is not None
            for req in req_list
        )
        checks.append(("has_priority", has_priority))

        result = self._make_result(checks)

        # Add specific feedback for common issues
        if not ears_valid:
            result.feedback_for_retry = (
                "Requirements must follow EARS format. Each requirement should have "
                "a 'condition' field that starts with 'WHEN' (e.g., 'WHEN a user submits a form'). "
                "Please regenerate with proper EARS format."
            )

        if not has_criteria:
            if result.feedback_for_retry:
                result.feedback_for_retry += "\n\n"
            else:
                result.feedback_for_retry = ""
            result.feedback_for_retry += (
                "Each requirement must have at least 2 acceptance criteria. "
                "Criteria should be in Given/When/Then format or testable statements."
            )

        return result

    def _has_ears_condition(self, condition: str) -> bool:
        """Check if condition follows EARS format (starts with WHEN)."""
        if not condition:
            return False
        condition_upper = condition.strip().upper()
        return condition_upper.startswith("WHEN")

    def _get_criteria(self, req: dict) -> list[str]:
        """Extract criteria text from requirement."""
        criteria = req.get("criteria", [])
        if not criteria:
            criteria = req.get("acceptance_criteria", [])

        result = []
        for c in criteria:
            if isinstance(c, dict):
                result.append(c.get("text", ""))
            elif isinstance(c, str):
                result.append(c)
        return [c for c in result if c]

    def _is_testable(self, criteria_text: str) -> bool:
        """Check if criteria text contains testable action words."""
        text_lower = criteria_text.lower()
        return any(word in text_lower for word in self.TESTABLE_WORDS)
