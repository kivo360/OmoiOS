"""Validation system API routes for task validation workflow."""

from typing import Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from omoi_os.services.validation_orchestrator import ValidationOrchestrator

router = APIRouter()


# Request/Response Models (matching REQ-VAL-API)


class GiveReviewRequest(BaseModel):
    """Request to submit validation review (REQ-VAL-API)."""

    task_id: str = Field(..., description="ID of task being reviewed")
    validator_agent_id: str = Field(
        ..., description="ID of validator agent submitting review"
    )
    validation_passed: bool = Field(..., description="Whether validation passed")
    feedback: str = Field(..., description="Feedback text (required)")
    evidence: Optional[Dict] = Field(None, description="Optional evidence dict")
    recommendations: Optional[list[str]] = Field(
        None, description="Optional list of recommendations"
    )


class GiveReviewResponse(BaseModel):
    """Response for validation review submission."""

    status: str = Field(..., description="Status: 'completed' or 'needs_work'")
    message: str = Field(..., description="Status message")
    iteration: int = Field(..., description="Current validation iteration number")


class SpawnValidatorRequest(BaseModel):
    """Request to spawn validator agent (REQ-VAL-API)."""

    task_id: str = Field(..., description="ID of task to spawn validator for")
    commit_sha: Optional[str] = Field(
        None, description="Optional Git commit SHA for validation"
    )


class SpawnValidatorResponse(BaseModel):
    """Response for validator spawn."""

    validator_agent_id: str = Field(..., description="ID of spawned validator agent")


class SendFeedbackRequest(BaseModel):
    """Request to deliver feedback to agent (REQ-VAL-API)."""

    agent_id: str = Field(..., description="ID of agent to send feedback to")
    feedback: str = Field(..., description="Feedback text to deliver")


class SendFeedbackResponse(BaseModel):
    """Response for feedback delivery."""

    delivered: bool = Field(..., description="Whether feedback was delivered")


class ValidationStatusResponse(BaseModel):
    """Response for validation status query (REQ-VAL-API)."""

    task_id: str = Field(..., description="Task ID")
    state: str = Field(..., description="Current validation state")
    iteration: int = Field(..., description="Current validation iteration")
    review_done: bool = Field(
        ..., description="Whether latest validation cycle completed successfully"
    )
    last_feedback: Optional[str] = Field(None, description="Last validation feedback")


# Dependency Injection


def get_validation_orchestrator() -> ValidationOrchestrator:
    """Get validation orchestrator instance from app state."""
    from omoi_os.api.main import validation_orchestrator

    if not validation_orchestrator:
        raise HTTPException(
            status_code=503, detail="Validation orchestrator service not available"
        )

    return validation_orchestrator


# API Endpoints (REQ-VAL-API)


@router.post("/give_review", response_model=GiveReviewResponse)
def give_review(
    request: GiveReviewRequest,
    orchestrator: ValidationOrchestrator = Depends(get_validation_orchestrator),
) -> GiveReviewResponse:
    """Submit validation review for a task (REQ-VAL-API, REQ-VAL-SEC-001).

    Preconditions:
        - validator_agent_id must be a validator agent
        - task must be in validation_in_progress state
        - feedback must be non-empty if validation_passed=False

    Args:
        request: GiveReviewRequest with review details
        orchestrator: Validation orchestrator service

    Returns:
        GiveReviewResponse with status, message, and iteration

    Raises:
        400: Bad request (invalid state, missing feedback, etc.)
        403: Forbidden (non-validator agent)
        404: Task not found
    """
    try:
        result = orchestrator.give_review(
            task_id=request.task_id,
            validator_agent_id=request.validator_agent_id,
            validation_passed=request.validation_passed,
            feedback=request.feedback,
            evidence=request.evidence,
            recommendations=request.recommendations,
        )
        return GiveReviewResponse(**result)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/spawn_validator", response_model=SpawnValidatorResponse)
def spawn_validator(
    request: SpawnValidatorRequest,
    orchestrator: ValidationOrchestrator = Depends(get_validation_orchestrator),
) -> SpawnValidatorResponse:
    """Spawn validator agent for task (REQ-VAL-API, REQ-VAL-LC-001).

    Args:
        request: SpawnValidatorRequest with task_id and optional commit_sha
        orchestrator: Validation orchestrator service

    Returns:
        SpawnValidatorResponse with validator_agent_id

    Raises:
        404: Task not found
        409: Validator already running for this task
    """
    validator_id = orchestrator.spawn_validator(
        task_id=request.task_id,
        commit_sha=request.commit_sha,
    )

    if not validator_id:
        # Check if task exists
        status = orchestrator.get_validation_status(request.task_id)
        if status is None:
            raise HTTPException(status_code=404, detail="task_not_found")
        else:
            # Validator already running
            raise HTTPException(status_code=409, detail="validator_already_running")

    return SpawnValidatorResponse(validator_agent_id=validator_id)


@router.post("/send_feedback", response_model=SendFeedbackResponse)
def send_feedback(
    request: SendFeedbackRequest,
    orchestrator: ValidationOrchestrator = Depends(get_validation_orchestrator),
) -> SendFeedbackResponse:
    """Deliver validation feedback to agent (REQ-VAL-API, REQ-VAL-LC-002).

    Args:
        request: SendFeedbackRequest with agent_id and feedback
        orchestrator: Validation orchestrator service

    Returns:
        SendFeedbackResponse with delivered flag

    Raises:
        404: Agent not found
    """
    delivered = orchestrator.send_feedback(
        agent_id=request.agent_id,
        feedback=request.feedback,
    )

    if not delivered:
        raise HTTPException(status_code=404, detail="agent_not_found")

    return SendFeedbackResponse(delivered=True)


@router.get("/status", response_model=ValidationStatusResponse)
def get_validation_status(
    task_id: str = Query(..., description="Task ID to query"),
    orchestrator: ValidationOrchestrator = Depends(get_validation_orchestrator),
) -> ValidationStatusResponse:
    """Fetch validation status for task (REQ-VAL-API).

    Args:
        task_id: Task ID to query (query parameter)
        orchestrator: Validation orchestrator service

    Returns:
        ValidationStatusResponse with task_id, state, iteration, review_done, last_feedback

    Raises:
        404: Task not found
    """
    status = orchestrator.get_validation_status(task_id)

    if status is None:
        raise HTTPException(status_code=404, detail="task_not_found")

    return ValidationStatusResponse(**status)
