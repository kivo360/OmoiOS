"""Result submission API routes for task-level and workflow-level results."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.models.agent_result import AgentResult
from omoi_os.models.workflow_result import WorkflowResult
from omoi_os.services.result_submission import ResultSubmissionService

router = APIRouter()


def serialize_agent_result(result: AgentResult) -> Dict:
    """Convert AgentResult ORM object into API-friendly dict."""
    return {
        "result_id": result.id,
        "agent_id": result.agent_id,
        "task_id": result.task_id,
        "markdown_file_path": result.markdown_file_path,
        "result_type": result.result_type,
        "summary": result.summary,
        "verification_status": result.verification_status,
        "verified_at": result.verified_at.isoformat() if result.verified_at else None,
        "verified_by_validation_id": result.verified_by_validation_id,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


def serialize_workflow_result(result: WorkflowResult) -> Dict:
    """Convert WorkflowResult ORM object into API-friendly dict."""
    return {
        "result_id": result.id,
        "workflow_id": result.workflow_id,
        "agent_id": result.agent_id,
        "markdown_file_path": result.markdown_file_path,
        "explanation": result.explanation,
        "evidence": result.evidence,
        "status": result.status,
        "validated_at": result.validated_at.isoformat() if result.validated_at else None,
        "validation_feedback": result.validation_feedback,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


# Request/Response Models

class ReportResultsRequest(BaseModel):
    """Request to submit task-level results."""
    task_id: str = Field(..., description="ID of task being reported on")
    markdown_file_path: str = Field(..., description="Path to markdown result file")
    result_type: str = Field(..., description="Type: implementation, analysis, fix, design, test, documentation")
    summary: str = Field(..., description="Brief summary of results")


class SubmitResultRequest(BaseModel):
    """Request to submit workflow-level result."""
    workflow_id: str = Field(..., description="ID of workflow (ticket)")
    markdown_file_path: str = Field(..., description="Path to result markdown file")
    explanation: Optional[str] = Field(None, description="What was accomplished")
    evidence: Optional[List[str]] = Field(None, description="Evidence items")


class ValidateResultRequest(BaseModel):
    """Request to validate workflow result."""
    result_id: str = Field(..., description="ID of workflow result to validate")
    validation_passed: bool = Field(..., description="Whether validation passed")
    feedback: str = Field(..., description="Detailed validation feedback")
    evidence: List[dict] = Field(default_factory=list, description="Evidence items checked")


class AgentResultDTO(BaseModel):
    """Agent result response model."""
    result_id: str
    agent_id: str
    task_id: str
    markdown_file_path: str
    result_type: str
    summary: str
    verification_status: str
    verified_at: Optional[str]
    verified_by_validation_id: Optional[str]
    created_at: Optional[str]

    model_config = ConfigDict(json_schema_extra={"example": {
        "result_id": "uuid",
        "agent_id": "agent-uuid",
        "task_id": "task-uuid",
        "markdown_file_path": "/path/to/results.md",
        "result_type": "implementation",
        "summary": "Implemented feature successfully",
        "verification_status": "unverified",
        "verified_at": None,
        "verified_by_validation_id": None,
        "created_at": "2025-11-17T12:00:00Z",
    }})


class WorkflowResultDTO(BaseModel):
    """Workflow result response model."""
    result_id: str
    workflow_id: str
    agent_id: str
    markdown_file_path: str
    explanation: Optional[str]
    evidence: Optional[dict]
    status: str
    validated_at: Optional[str]
    validation_feedback: Optional[str]
    created_at: Optional[str]

    model_config = ConfigDict(json_schema_extra={"example": {
        "result_id": "uuid",
        "workflow_id": "workflow-uuid",
        "agent_id": "agent-uuid",
        "markdown_file_path": "/path/to/solution.md",
        "explanation": "Found the solution",
        "evidence": {"items": ["Evidence 1", "Evidence 2"]},
        "status": "pending_validation",
        "validated_at": None,
        "validation_feedback": None,
        "created_at": "2025-11-17T12:00:00Z",
    }})


class SubmitResultResponse(BaseModel):
    """Response for workflow result submission."""
    status: str
    result_id: str
    workflow_id: str
    agent_id: str
    validation_triggered: bool
    message: str
    created_at: str


# Dependency injection
def get_result_service() -> ResultSubmissionService:
    """Get result submission service instance."""
    from omoi_os.api.dependencies import get_db_service, get_event_bus
    from omoi_os.services.phase_loader import PhaseLoader
    
    db = get_db_service()
    event_bus = get_event_bus()
    phase_loader = PhaseLoader()
    return ResultSubmissionService(db=db, event_bus=event_bus, phase_loader=phase_loader)


# Routes

@router.post(
    "/report_results",
    response_model=AgentResultDTO,
    status_code=200,
    summary="Submit task-level results",
)
def report_task_results(
    request: ReportResultsRequest,
    agent_id: str = Header(..., alias="X-Agent-ID"),
    result_service: ResultSubmissionService = Depends(get_result_service),
) -> AgentResultDTO:
    """Submit task-level results (AgentResult).
    
    Agents submit results for individual tasks with comprehensive evidence.
    Multiple results can be submitted per task.
    
    **File Validation:**
    - Must be markdown (.md)
    - Maximum 100KB
    - No path traversal
    
    **Requires:** Agent must own the task
    """
    try:
        result = result_service.report_task_result(
            agent_id=agent_id,
            task_id=request.task_id,
            markdown_file_path=request.markdown_file_path,
            result_type=request.result_type,
            summary=request.summary,
        )
        
        return AgentResultDTO(**serialize_agent_result(result))
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/submit_result",
    response_model=SubmitResultResponse,
    status_code=200,
    summary="Submit workflow-level result",
)
def submit_workflow_result(
    request: SubmitResultRequest,
    agent_id: str = Header(..., alias="X-Agent-ID"),
    result_service: ResultSubmissionService = Depends(get_result_service),
) -> SubmitResultResponse:
    """Submit workflow-level result (WorkflowResult).
    
    Marks workflow completion with definitive solution.
    Automatically triggers validation if workflow has has_result=true.
    
    **File Validation:**
    - Must be markdown (.md)
    - Maximum 100KB
    - No path traversal
    """
    try:
        result = result_service.submit_workflow_result(
            workflow_id=request.workflow_id,
            agent_id=agent_id,
            markdown_file_path=request.markdown_file_path,
            explanation=request.explanation,
            evidence=request.evidence,
        )
        
        # Check if workflow has result validation enabled
        validation_triggered = False
        try:
            config = result_service._load_workflow_config(request.workflow_id)
            validation_triggered = config.get("has_result", False)
        except Exception:
            pass
        
        return SubmitResultResponse(
            status="submitted",
            result_id=result.id,
            workflow_id=result.workflow_id,
            agent_id=result.agent_id,
            validation_triggered=validation_triggered,
            message="Result submitted successfully" + (
                " and validation triggered" if validation_triggered else ""
            ),
            created_at=result.created_at.isoformat(),
        )
    
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/submit_result_validation",
    status_code=200,
    summary="Validate workflow result (validator-only)",
)
def validate_workflow_result(
    request: ValidateResultRequest,
    validator_id: str = Header(..., alias="X-Validator-ID"),
    result_service: ResultSubmissionService = Depends(get_result_service),
) -> Dict:
    """Validate workflow result (validator agents only).
    
    Updates validation status and executes configured on_result_found action.
    
    **Actions:**
    - on_result_found="stop_all": Terminates workflow
    - on_result_found="do_nothing": Logs result, continues workflow
    
    **Requires:** Caller must be validator agent
    """
    try:
        validation_result = result_service.validate_workflow_result(
            result_id=request.result_id,
            passed=request.validation_passed,
            feedback=request.feedback,
            evidence=request.evidence,
            validator_agent_id=validator_id,
        )
        
        return {
            **validation_result,
            "message": f"Validation {'passed' if request.validation_passed else 'failed'} - {validation_result['action_taken']}",
        }
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/workflows/{workflow_id}/results",
    response_model=List[WorkflowResultDTO],
    status_code=200,
    summary="Get all results for a workflow",
)
def get_workflow_results(
    workflow_id: str,
    result_service: ResultSubmissionService = Depends(get_result_service),
) -> List[WorkflowResultDTO]:
    """Get all workflow-level results for a workflow.
    
    Returns results sorted by creation time.
    """
    results = result_service.list_workflow_results(workflow_id)
    return [WorkflowResultDTO(**serialize_workflow_result(r)) for r in results]


@router.get(
    "/tasks/{task_id}/results",
    response_model=List[AgentResultDTO],
    status_code=200,
    summary="Get all results for a task",
)
def get_task_results(
    task_id: str,
    result_service: ResultSubmissionService = Depends(get_result_service),
) -> List[AgentResultDTO]:
    """Get all task-level results for a task.
    
    Returns results sorted by creation time.
    Multiple results per task are supported.
    """
    results = result_service.get_task_results(task_id)
    return [AgentResultDTO(**serialize_agent_result(r)) for r in results]

