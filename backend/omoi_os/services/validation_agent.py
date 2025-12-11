"""Validation agent for phase gate reviews using PydanticAI."""

from __future__ import annotations

from typing import Any

from omoi_os.services.llm_service import get_llm_service
from omoi_os.schemas.validation_analysis import ValidationResult


class ValidationAgent:
    """Validation agent that uses PydanticAI for structured validation."""

    def __init__(
        self,
        workspace_dir: str,
    ):
        """
        Initialize validation agent.

        Args:
            workspace_dir: Directory path for workspace operations.
        """
        self.workspace_dir = workspace_dir

    async def validate_phase_completion(
        self,
        ticket_id: str,
        phase_id: str,
        artifacts: list[dict[str, Any]],
    ) -> ValidationResult:
        """
        Use PydanticAI to validate phase completion artifacts.

        Args:
            ticket_id: ID of the ticket being validated.
            phase_id: ID of the phase being validated.
            artifacts: List of artifact dictionaries to validate.

        Returns:
            ValidationResult with structured validation feedback.
        """
        # Build prompt using template
        from omoi_os.services.template_service import get_template_service

        template_service = get_template_service()
        prompt = template_service.render(
            "prompts/validation.md.j2",
            ticket_id=ticket_id,
            phase_id=phase_id,
            artifacts=artifacts,
        )

        system_prompt = template_service.render_system_prompt("system/validation.md.j2")

        # Run validation using LLM service
        llm = get_llm_service()
        return await llm.structured_output(
            prompt,
            output_type=ValidationResult,
            system_prompt=system_prompt,
        )

    def validate_phase_completion_sync(
        self,
        ticket_id: str,
        phase_id: str,
        artifacts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Synchronous fallback for validation (basic check).

        Args:
            ticket_id: ID of the ticket being validated.
            phase_id: ID of the phase being validated.
            artifacts: List of artifact dictionaries to validate.

        Returns:
            Dictionary with validation results.
        """
        # Basic validation: check if artifacts exist
        passed = len(artifacts) > 0
        return {
            "passed": passed,
            "feedback": f"Artifacts for ticket {ticket_id} in {phase_id} reviewed. "
            f"Found {len(artifacts)} artifacts.",
            "blocking_reasons": [] if passed else ["No artifacts found"],
            "completeness_score": min(1.0, len(artifacts) / 3.0),  # Assume 3+ is complete
            "missing_artifacts": [],
        }
