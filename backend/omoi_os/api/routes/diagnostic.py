"""Diagnostic system API routes for stuck workflow detection."""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from omoi_os.models.diagnostic_run import DiagnosticRun
from omoi_os.services.diagnostic import DiagnosticService

router = APIRouter()


def serialize_diagnostic_run(run: DiagnosticRun) -> Dict:
    """Convert DiagnosticRun ORM object into API-friendly dict."""
    return {
        "run_id": run.id,
        "workflow_id": run.workflow_id,
        "diagnostic_agent_id": run.diagnostic_agent_id,
        "diagnostic_task_id": run.diagnostic_task_id,
        "triggered_at": run.triggered_at.isoformat() if run.triggered_at else None,
        "total_tasks_at_trigger": run.total_tasks_at_trigger,
        "done_tasks_at_trigger": run.done_tasks_at_trigger,
        "failed_tasks_at_trigger": run.failed_tasks_at_trigger,
        "time_since_last_task_seconds": run.time_since_last_task_seconds,
        "tasks_created_count": run.tasks_created_count,
        "tasks_created_ids": run.tasks_created_ids,
        "workflow_goal": run.workflow_goal,
        "phases_analyzed": run.phases_analyzed,
        "agents_reviewed": run.agents_reviewed,
        "diagnosis": run.diagnosis,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "status": run.status,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


# Response Models


class DiagnosticRunDTO(BaseModel):
    """Diagnostic run response model."""

    run_id: str
    workflow_id: str
    diagnostic_agent_id: str | None
    diagnostic_task_id: str | None
    triggered_at: str | None
    total_tasks_at_trigger: int
    done_tasks_at_trigger: int
    failed_tasks_at_trigger: int
    time_since_last_task_seconds: int
    tasks_created_count: int
    tasks_created_ids: dict | None
    workflow_goal: str | None
    phases_analyzed: dict | None
    agents_reviewed: dict | None
    diagnosis: str | None
    completed_at: str | None
    status: str
    created_at: str | None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "uuid",
                "workflow_id": "workflow-uuid",
                "diagnostic_agent_id": None,
                "diagnostic_task_id": None,
                "triggered_at": "2025-11-17T12:00:00Z",
                "total_tasks_at_trigger": 10,
                "done_tasks_at_trigger": 10,
                "failed_tasks_at_trigger": 0,
                "time_since_last_task_seconds": 300,
                "tasks_created_count": 2,
                "tasks_created_ids": {"task_ids": ["task-1", "task-2"]},
                "workflow_goal": "Complete implementation",
                "phases_analyzed": {},
                "agents_reviewed": {},
                "diagnosis": "Workflow missing result submission",
                "completed_at": "2025-11-17T12:05:00Z",
                "status": "completed",
                "created_at": "2025-11-17T12:00:00Z",
            }
        }
    )


# Dependency injection
def get_diagnostic_service() -> DiagnosticService:
    """Get diagnostic service instance."""
    from omoi_os.api.dependencies import get_db_service, get_event_bus
    from omoi_os.services.discovery import DiscoveryService
    from omoi_os.services.memory import MemoryService
    from omoi_os.services.monitor import MonitorService
    from omoi_os.services.embedding import EmbeddingService

    db = get_db_service()
    event_bus = get_event_bus()

    # Initialize required services
    embedding = EmbeddingService()
    memory = MemoryService(embedding_service=embedding, event_bus=event_bus)
    discovery = DiscoveryService(event_bus=event_bus)
    monitor = MonitorService(db=db, event_bus=event_bus)

    return DiagnosticService(
        db=db,
        discovery=discovery,
        memory=memory,
        monitor=monitor,
        event_bus=event_bus,
    )


# Routes


@router.get(
    "/stuck-workflows",
    status_code=200,
    summary="List currently stuck workflows",
)
def get_stuck_workflows(
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service),
) -> Dict:
    """Get workflows that are currently stuck.

    A workflow is stuck when:
    - All tasks are finished
    - No validated result exists
    - Been stuck for at least 60 seconds
    """
    stuck = diagnostic_service.find_stuck_workflows(
        cooldown_seconds=60,
        stuck_threshold_seconds=60,
    )

    return {
        "stuck_count": len(stuck),
        "stuck_workflows": stuck,
    }


@router.get(
    "/runs",
    response_model=List[DiagnosticRunDTO],
    status_code=200,
    summary="Get diagnostic run history",
)
def get_diagnostic_runs(
    limit: int = 100,
    workflow_id: str | None = None,
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service),
) -> List[DiagnosticRunDTO]:
    """Get diagnostic run history.

    Returns diagnostic runs sorted by most recent first.
    """
    runs = diagnostic_service.get_diagnostic_runs(
        workflow_id=workflow_id,
        limit=limit,
    )

    return [DiagnosticRunDTO(**serialize_diagnostic_run(run)) for run in runs]


@router.post(
    "/trigger/{workflow_id}",
    response_model=DiagnosticRunDTO,
    status_code=200,
    summary="Manually trigger diagnostic for workflow",
)
async def manual_trigger_diagnostic(
    workflow_id: str,
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service),
) -> DiagnosticRunDTO:
    """Manually trigger diagnostic agent for a stuck workflow.

    Bypasses cooldown and stuck time checks.
    """
    # Build context
    context = diagnostic_service.build_diagnostic_context(workflow_id)

    if not context:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    # Load diagnostic settings for max_tasks
    from omoi_os.config import get_app_settings

    app_settings = get_app_settings()
    max_tasks = app_settings.diagnostic.max_tasks_per_run

    # Spawn diagnostic (async)
    diagnostic_run = await diagnostic_service.spawn_diagnostic_agent(
        workflow_id=workflow_id,
        context=context,
        max_tasks=max_tasks,
    )

    return DiagnosticRunDTO(**serialize_diagnostic_run(diagnostic_run))


@router.get(
    "/runs/{run_id}",
    response_model=DiagnosticRunDTO,
    status_code=200,
    summary="Get diagnostic run details",
)
def get_diagnostic_details(
    run_id: str,
    diagnostic_service: DiagnosticService = Depends(get_diagnostic_service),
) -> DiagnosticRunDTO:
    """Get detailed information about a specific diagnostic run."""
    runs = diagnostic_service.get_diagnostic_runs(limit=1000)  # Get all to search

    run = next((r for r in runs if r.id == run_id), None)
    if not run:
        raise HTTPException(
            status_code=404, detail=f"Diagnostic run {run_id} not found"
        )

    return DiagnosticRunDTO(**serialize_diagnostic_run(run))
