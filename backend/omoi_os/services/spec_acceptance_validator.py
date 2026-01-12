"""Spec Acceptance Criteria Validator.

Validates that completed tasks meet their associated spec acceptance criteria.

This service:
1. Links Tasks back to their SpecTasks via task.result["spec_task_id"]
2. Gets the associated SpecRequirements and their AcceptanceCriteria
3. Validates if criteria are met based on implementation evidence
4. Updates criterion.completed status

Integration with existing validation:
- TaskValidatorService checks code quality (tests, build, PR)
- SpecAcceptanceValidator checks spec acceptance criteria
- Both can run as part of the validation workflow
"""

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from omoi_os.logging import get_logger
from omoi_os.models.spec import Spec, SpecAcceptanceCriterion, SpecRequirement, SpecTask
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.llm_service import LLMService, get_llm_service

logger = get_logger(__name__)


@dataclass
class CriterionResult:
    """Result of validating a single acceptance criterion."""

    criterion_id: str
    criterion_text: str
    met: bool
    confidence: float  # 0.0 to 1.0
    evidence: str
    reasoning: str


@dataclass
class ValidationResult:
    """Result of validating all acceptance criteria for a task."""

    task_id: str
    spec_task_id: Optional[str]
    criteria_results: list[CriterionResult] = field(default_factory=list)
    all_criteria_met: bool = False
    total_criteria: int = 0
    criteria_met_count: int = 0
    error: Optional[str] = None

    @property
    def completion_percentage(self) -> float:
        """Calculate percentage of criteria met."""
        if self.total_criteria == 0:
            return 100.0
        return (self.criteria_met_count / self.total_criteria) * 100


class SpecAcceptanceValidator:
    """Validates tasks against spec acceptance criteria.

    This validator:
    1. Gets the SpecTask linked to a Task (via task.result["spec_task_id"])
    2. Finds requirements linked to that spec
    3. Validates each acceptance criterion using LLM analysis
    4. Updates criterion completion status in the database
    """

    def __init__(
        self,
        db: DatabaseService,
        llm_service: Optional[LLMService] = None,
        event_bus: Optional[EventBusService] = None,
    ):
        """Initialize the validator.

        Args:
            db: Database service for persistence
            llm_service: LLM service for intelligent validation
            event_bus: Optional event bus for publishing validation events
        """
        self.db = db
        self.llm_service = llm_service or get_llm_service()
        self.event_bus = event_bus

    async def validate_task(
        self,
        task_id: str,
        implementation_evidence: Optional[dict] = None,
    ) -> ValidationResult:
        """Validate a task against its spec acceptance criteria.

        Args:
            task_id: ID of the Task to validate
            implementation_evidence: Optional evidence from implementation
                (PR diff, test results, etc.)

        Returns:
            ValidationResult with all criterion evaluations
        """
        result = ValidationResult(task_id=task_id, spec_task_id=None)

        async with self.db.get_async_session() as session:
            # Get the task
            task_result = await session.execute(
                select(Task).filter(Task.id == task_id)
            )
            task = task_result.scalar_one_or_none()

            if not task:
                result.error = f"Task not found: {task_id}"
                return result

            # Get spec_task_id from task result
            if not task.result:
                result.error = "Task has no result data - cannot find spec_task_id"
                return result

            spec_task_id = task.result.get("spec_task_id")
            if not spec_task_id:
                # Not a spec-driven task, skip acceptance validation
                logger.debug(
                    "task_not_spec_driven",
                    task_id=task_id,
                    message="Task has no spec_task_id, skipping acceptance validation",
                )
                result.all_criteria_met = True  # Non-spec tasks pass by default
                return result

            result.spec_task_id = spec_task_id

            # Get the SpecTask with its Spec
            spec_task_result = await session.execute(
                select(SpecTask)
                .filter(SpecTask.id == spec_task_id)
                .options(selectinload(SpecTask.spec))
            )
            spec_task = spec_task_result.scalar_one_or_none()

            if not spec_task:
                result.error = f"SpecTask not found: {spec_task_id}"
                return result

            # Get the Spec with requirements and their criteria
            spec_result = await session.execute(
                select(Spec)
                .filter(Spec.id == spec_task.spec_id)
                .options(
                    selectinload(Spec.requirements).selectinload(
                        SpecRequirement.criteria
                    )
                )
            )
            spec = spec_result.scalar_one_or_none()

            if not spec:
                result.error = f"Spec not found: {spec_task.spec_id}"
                return result

            # Collect all acceptance criteria from this spec's requirements
            all_criteria: list[SpecAcceptanceCriterion] = []
            for requirement in spec.requirements:
                all_criteria.extend(requirement.criteria)

            if not all_criteria:
                logger.info(
                    "no_acceptance_criteria",
                    spec_id=spec.id,
                    message="Spec has no acceptance criteria, auto-passing",
                )
                result.all_criteria_met = True
                return result

            result.total_criteria = len(all_criteria)

            # Build implementation context for LLM validation
            implementation_context = self._build_implementation_context(
                task=task,
                spec_task=spec_task,
                spec=spec,
                evidence=implementation_evidence,
            )

            # Validate each criterion
            for criterion in all_criteria:
                criterion_result = await self._validate_criterion(
                    criterion=criterion,
                    implementation_context=implementation_context,
                    task_description=task.description,
                )
                result.criteria_results.append(criterion_result)

                if criterion_result.met:
                    result.criteria_met_count += 1
                    # Update criterion in database
                    criterion.completed = True

            # Commit criterion updates
            await session.commit()

            result.all_criteria_met = (
                result.criteria_met_count == result.total_criteria
            )

        # Publish validation event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="SPEC_CRITERIA_VALIDATED",
                    entity_type="task",
                    entity_id=task_id,
                    payload={
                        "spec_task_id": spec_task_id,
                        "all_criteria_met": result.all_criteria_met,
                        "total_criteria": result.total_criteria,
                        "criteria_met_count": result.criteria_met_count,
                        "completion_percentage": result.completion_percentage,
                    },
                )
            )

        logger.info(
            "spec_criteria_validated",
            task_id=task_id,
            spec_task_id=spec_task_id,
            criteria_met=f"{result.criteria_met_count}/{result.total_criteria}",
            all_met=result.all_criteria_met,
        )

        return result

    def _build_implementation_context(
        self,
        task: Task,
        spec_task: SpecTask,
        spec: Spec,
        evidence: Optional[dict],
    ) -> str:
        """Build context string for LLM validation.

        Args:
            task: The execution Task
            spec_task: The SpecTask being validated
            spec: The parent Spec
            evidence: Implementation evidence (PR diff, test results, etc.)

        Returns:
            Formatted context string
        """
        context_parts = [
            f"# Implementation Context\n",
            f"## Spec: {spec.title}",
            f"Spec Description: {spec.description or 'N/A'}",
            f"\n## Task: {spec_task.title}",
            f"Task Description: {spec_task.description or task.description or 'N/A'}",
            f"Task Phase: {spec_task.phase}",
            f"Task Status: {task.status}",
        ]

        # Add implementation result if available
        if task.result:
            result_summary = task.result.get("implementation_result", {})
            if result_summary:
                context_parts.append("\n## Implementation Result")
                for key, value in result_summary.items():
                    if isinstance(value, str) and len(value) > 500:
                        value = value[:500] + "..."
                    context_parts.append(f"- {key}: {value}")

        # Add evidence if provided
        if evidence:
            context_parts.append("\n## Evidence")
            for key, value in evidence.items():
                if isinstance(value, str) and len(value) > 500:
                    value = value[:500] + "..."
                context_parts.append(f"- {key}: {value}")

        return "\n".join(context_parts)

    async def _validate_criterion(
        self,
        criterion: SpecAcceptanceCriterion,
        implementation_context: str,
        task_description: Optional[str],
    ) -> CriterionResult:
        """Validate a single acceptance criterion using LLM.

        Args:
            criterion: The criterion to validate
            implementation_context: Context about the implementation
            task_description: Description of what the task should do

        Returns:
            CriterionResult with validation outcome
        """
        from pydantic import BaseModel, Field

        class CriterionValidation(BaseModel):
            """LLM output for criterion validation."""

            met: bool = Field(
                description="Whether the criterion is met based on the evidence"
            )
            confidence: float = Field(
                ge=0.0,
                le=1.0,
                description="Confidence level (0.0 to 1.0) in the assessment",
            )
            evidence: str = Field(
                description="Specific evidence that supports this assessment"
            )
            reasoning: str = Field(
                description="Explanation of why the criterion is or isn't met"
            )

        prompt = f"""You are evaluating whether an acceptance criterion has been met based on the implementation context.

## Acceptance Criterion
"{criterion.text}"

{implementation_context}

## Task Description
{task_description or "No description available"}

## Your Task
Evaluate whether this acceptance criterion has been met based on the implementation context and evidence provided.

Consider:
1. Does the implementation address what the criterion requires?
2. Is there evidence that the criterion's requirements are satisfied?
3. Are there any gaps between what was implemented and what the criterion requires?

If the implementation directly addresses the criterion's requirements and there's evidence of completion, mark it as met.
If the implementation doesn't address the criterion or there's insufficient evidence, mark it as not met.
"""

        try:
            validation = await self.llm_service.structured_output(
                prompt=prompt,
                output_type=CriterionValidation,
                system_prompt=(
                    "You are an expert software engineer validating acceptance criteria. "
                    "Be thorough but fair - only mark criteria as unmet if there's clear "
                    "evidence they weren't addressed."
                ),
                output_retries=2,
            )

            return CriterionResult(
                criterion_id=criterion.id,
                criterion_text=criterion.text,
                met=validation.met,
                confidence=validation.confidence,
                evidence=validation.evidence,
                reasoning=validation.reasoning,
            )

        except Exception as e:
            logger.error(
                "criterion_validation_failed",
                criterion_id=criterion.id,
                error=str(e),
            )
            # On LLM failure, mark as unmet with low confidence
            return CriterionResult(
                criterion_id=criterion.id,
                criterion_text=criterion.text,
                met=False,
                confidence=0.0,
                evidence="",
                reasoning=f"Validation failed: {str(e)}",
            )

    async def get_spec_criteria_status(self, spec_id: str) -> dict:
        """Get the status of all acceptance criteria for a spec.

        Args:
            spec_id: Spec ID to get criteria status for

        Returns:
            Status dict with criteria counts and completion percentage
        """
        async with self.db.get_async_session() as session:
            # Get spec with requirements and criteria
            result = await session.execute(
                select(Spec)
                .filter(Spec.id == spec_id)
                .options(
                    selectinload(Spec.requirements).selectinload(
                        SpecRequirement.criteria
                    )
                )
            )
            spec = result.scalar_one_or_none()

            if not spec:
                return {"error": "Spec not found"}

            total_criteria = 0
            completed_criteria = 0
            criteria_by_requirement: dict[str, dict] = {}

            for requirement in spec.requirements:
                req_total = len(requirement.criteria)
                req_completed = sum(1 for c in requirement.criteria if c.completed)
                total_criteria += req_total
                completed_criteria += req_completed

                criteria_by_requirement[requirement.id] = {
                    "requirement_title": requirement.title,
                    "total": req_total,
                    "completed": req_completed,
                    "criteria": [
                        {
                            "id": c.id,
                            "text": c.text,
                            "completed": c.completed,
                        }
                        for c in requirement.criteria
                    ],
                }

            return {
                "spec_id": spec_id,
                "total_criteria": total_criteria,
                "completed_criteria": completed_criteria,
                "completion_percentage": (
                    (completed_criteria / total_criteria * 100)
                    if total_criteria > 0
                    else 100.0
                ),
                "all_complete": completed_criteria == total_criteria and total_criteria > 0,
                "by_requirement": criteria_by_requirement,
            }


def get_spec_acceptance_validator(
    db: Optional[DatabaseService] = None,
    llm_service: Optional[LLMService] = None,
    event_bus: Optional[EventBusService] = None,
) -> SpecAcceptanceValidator:
    """Get SpecAcceptanceValidator instance.

    Args:
        db: Database service (will be auto-created if not provided)
        llm_service: LLM service for intelligent validation
        event_bus: Event bus for publishing events

    Returns:
        SpecAcceptanceValidator instance
    """
    if db is None:
        from omoi_os.api.dependencies import get_db_service
        db = get_db_service()

    return SpecAcceptanceValidator(
        db=db,
        llm_service=llm_service,
        event_bus=event_bus,
    )
