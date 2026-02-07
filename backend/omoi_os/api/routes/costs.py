"""Cost tracking and budget API routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from omoi_os.api.dependencies import (
    get_cost_tracking_service,
    get_budget_enforcer_service,
)
from omoi_os.services.cost_tracking import CostTrackingService
from omoi_os.services.budget_enforcer import BudgetEnforcerService

router = APIRouter()


# Request/Response Models


class CostRecordResponse(BaseModel):
    """Response model for cost record."""

    id: str  # UUID string (matches CostRecord ORM model)
    task_id: str
    agent_id: str | None
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    prompt_cost: float
    completion_cost: float
    total_cost: float
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CostSummaryResponse(BaseModel):
    """Response model for cost summary."""

    scope_type: str
    scope_id: str | None
    total_cost: float
    total_tokens: int
    record_count: int
    breakdown: list[dict]


class BudgetCreate(BaseModel):
    """Request model for creating a budget."""

    scope_type: str = Field(
        ..., description="Budget scope: global, ticket, agent, or phase"
    )
    scope_id: str | None = Field(
        None, description="ID of scoped entity (required unless global)"
    )
    limit_amount: float = Field(..., gt=0, description="Maximum allowed spend (USD)")
    period_end: datetime | None = Field(
        None, description="Budget period end (None for indefinite)"
    )
    alert_threshold: float = Field(
        0.8, ge=0, le=1, description="Alert at this percentage (0.0-1.0)"
    )


class BudgetResponse(BaseModel):
    """Response model for budget."""

    id: int
    scope_type: str
    scope_id: str | None
    limit_amount: float
    spent_amount: float
    remaining_amount: float
    period_start: datetime
    period_end: datetime | None
    alert_threshold: float
    alert_triggered: bool
    utilization_percent: float
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetCheckResponse(BaseModel):
    """Response model for budget check."""

    exists: bool
    limit: float | None
    spent: float
    remaining: float | None
    utilization_percent: float
    exceeded: bool
    alert_threshold: float | None = None
    alert_triggered: bool | None = None


class ForecastRequest(BaseModel):
    """Request model for cost forecasting."""

    pending_task_count: int = Field(..., gt=0, description="Number of pending tasks")
    avg_tokens_per_task: int | None = Field(
        None, description="Average tokens per task (uses default if not provided)"
    )
    provider: str = Field("anthropic", description="LLM provider for cost calculation")
    model: str = Field("claude-sonnet-4.5", description="Model for cost calculation")


class ForecastResponse(BaseModel):
    """Response model for cost forecast."""

    task_count: int
    estimated_cost: float
    estimated_tokens: int
    avg_tokens_per_task: int
    buffer_multiplier: float


# API Endpoints


@router.get("/records", response_model=list[CostRecordResponse])
async def list_cost_records(
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service),
):
    """
    List cost records, optionally filtered by task or agent.

    Returns up to `limit` most recent cost records.
    """
    with cost_service.db.get_session() as session:
        if task_id:
            records = cost_service.get_task_costs(task_id, session)
        elif agent_id:
            records = cost_service.get_agent_costs(agent_id, session)
        else:
            # Get all records (limited)
            from sqlalchemy import select
            from omoi_os.models.cost_record import CostRecord

            result = session.execute(
                select(CostRecord).order_by(CostRecord.recorded_at.desc()).limit(limit)
            )
            records = list(result.scalars().all())

        return [CostRecordResponse.model_validate(r) for r in records[:limit]]


@router.get("/summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    scope_type: str = Query(
        ..., description="Scope type: global, ticket, agent, phase, or task"
    ),
    scope_id: Optional[str] = Query(
        None, description="Scope ID (required unless scope_type=global)"
    ),
    cost_service: CostTrackingService = Depends(get_cost_tracking_service),
):
    """
    Get cost summary for a specific scope.

    Aggregates costs by provider and model, showing total spend and token usage.
    """
    if scope_type not in ["global", "ticket", "agent", "phase", "task"]:
        raise HTTPException(status_code=400, detail=f"Invalid scope_type: {scope_type}")

    if scope_type != "global" and not scope_id:
        raise HTTPException(
            status_code=400, detail=f"scope_id required for scope_type={scope_type}"
        )

    summary = cost_service.get_cost_summary(scope_type, scope_id)
    return CostSummaryResponse(**summary)


@router.get("/budgets", response_model=list[BudgetResponse])
async def list_budgets(
    scope_type: Optional[str] = Query(None, description="Filter by scope type"),
    budget_service: BudgetEnforcerService = Depends(get_budget_enforcer_service),
):
    """
    List all budgets, optionally filtered by scope type.
    """
    budgets = budget_service.list_budgets(scope_type)
    return [BudgetResponse(**b.to_dict()) for b in budgets]


@router.post("/budgets", response_model=BudgetResponse)
async def create_budget(
    budget_data: BudgetCreate,
    budget_service: BudgetEnforcerService = Depends(get_budget_enforcer_service),
):
    """
    Create a new budget limit.

    Budget limits can be scoped to:
    - global: System-wide budget
    - ticket: Per-ticket budget
    - agent: Per-agent budget
    - phase: Per-phase budget
    """
    try:
        budget = budget_service.create_budget(
            scope_type=budget_data.scope_type,
            limit_amount=budget_data.limit_amount,
            scope_id=budget_data.scope_id,
            period_end=budget_data.period_end,
            alert_threshold=budget_data.alert_threshold,
        )
        return BudgetResponse(**budget.to_dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/budgets/check", response_model=BudgetCheckResponse)
async def check_budget(
    scope_type: str = Query(..., description="Scope type to check"),
    scope_id: Optional[str] = Query(None, description="Scope ID"),
    budget_service: BudgetEnforcerService = Depends(get_budget_enforcer_service),
):
    """
    Check budget status for a scope.

    Returns current budget utilization and whether the limit has been exceeded.
    """
    status = budget_service.check_budget(scope_type, scope_id)
    return BudgetCheckResponse(**status)


@router.post("/forecast", response_model=ForecastResponse)
async def forecast_costs(
    forecast_data: ForecastRequest,
    cost_service: CostTrackingService = Depends(get_cost_tracking_service),
):
    """
    Forecast costs for pending tasks.

    Estimates total cost based on:
    - Number of pending tasks
    - Average tokens per task (configurable or uses default)
    - Provider and model pricing
    - Safety buffer multiplier
    """
    forecast = cost_service.forecast_costs(
        pending_task_count=forecast_data.pending_task_count,
        avg_tokens_per_task=forecast_data.avg_tokens_per_task,
        provider=forecast_data.provider,
        model=forecast_data.model,
    )
    return ForecastResponse(**forecast)
