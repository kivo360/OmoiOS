"""Usage — spec §18 §2 canonical SDK resource.

Two routes:
  GET /api/v1/usage                       → org-level summary (alias)
  GET /api/v1/usage/sessions/{session_id} → per-session aggregation

The org summary reuses `billing_service.get_usage_summary` so we don't
double-publish that logic. Per-session aggregation reads `cost_records`
directly (prompt_tokens / completion_tokens) plus Task timestamps for
compute_seconds — mapping spec §02 §Session `usage.tokens_input/output/
compute_seconds` onto our existing per-call cost rows.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from omoi_os.api.dependencies import (
    get_current_user,
    get_db_service,
    get_user_organization_ids,
    verify_task_access,
)
from omoi_os.logging import get_logger
from omoi_os.models.cost_record import CostRecord
from omoi_os.models.task import Task
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


class UsageSummary(BaseModel):
    """Org-level summary — thin mirror of BillingService.get_usage_summary."""

    organization_id: Optional[str] = None
    subscription_tier: Optional[str] = None
    workflows_used: int = 0
    workflows_limit: int = 0
    free_workflows_remaining: int = 0
    credit_balance: float = 0.0
    can_execute: bool = True
    reason: str = ""


class SessionUsage(BaseModel):
    """Per-session usage breakdown — matches spec §02 §Session.usage shape.

    `compute_seconds` is derived from task started_at/completed_at.
    `tokens_input`/`tokens_output` are summed from `cost_records` by task_id.
    """

    session_id: str
    compute_seconds: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0
    total_cost: float = 0.0


@router.get("", response_model=UsageSummary)
async def get_current_usage(
    organization_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
) -> UsageSummary:
    """Current-period org-level usage summary.

    `organization_id` defaults to the caller's first org membership when
    not supplied. Multi-org users can pass it explicitly to target a
    specific tenant.
    """
    from uuid import UUID as _UUID

    if organization_id is None:
        org_ids = await get_user_organization_ids(current_user, db)
        if not org_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User has no organization membership",
            )
        target_org = org_ids[0]
    else:
        try:
            target_org = _UUID(organization_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="organization_id must be a UUID",
            )
        org_ids = await get_user_organization_ids(current_user, db)
        if target_org not in org_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )

    from omoi_os.services.billing_service import get_billing_service

    billing_service = get_billing_service(db)
    summary = billing_service.get_usage_summary(target_org)
    return UsageSummary(organization_id=str(target_org), **summary)


@router.get("/sessions/{session_id}", response_model=SessionUsage)
async def get_session_usage(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DatabaseService = Depends(get_db_service),
) -> SessionUsage:
    """Per-session usage breakdown.

    Access control: `verify_task_access` enforces the 5-step precedence
    chain (SessionACL → workspace-org → created_by → ticket chain → deny)
    from the session-ticket-decoupling plan — so this endpoint is
    reachable only to callers who can see the session itself. Called
    inline (rather than via `Depends`) so the path param `session_id`
    flows in as the `task_id` argument.
    """
    await verify_task_access(task_id=session_id, current_user=current_user, db=db)
    async with db.get_async_session() as session:
        # Aggregate tokens + cost from cost_records.
        stmt = select(
            func.coalesce(func.sum(CostRecord.prompt_tokens), 0),
            func.coalesce(func.sum(CostRecord.completion_tokens), 0),
            func.coalesce(func.sum(CostRecord.total_cost), 0.0),
        ).where(CostRecord.task_id == session_id)
        row = (await session.execute(stmt)).one()
        tokens_input, tokens_output, total_cost = row

        # compute_seconds — derive from the Task's lifecycle timestamps.
        task_row = (
            await session.execute(
                select(Task.started_at, Task.completed_at).where(Task.id == session_id)
            )
        ).first()
        compute_seconds = 0.0
        if task_row is not None and task_row.started_at is not None:
            end = task_row.completed_at or task_row.started_at
            try:
                compute_seconds = max(0.0, (end - task_row.started_at).total_seconds())
            except Exception:
                compute_seconds = 0.0

    return SessionUsage(
        session_id=session_id,
        compute_seconds=compute_seconds,
        tokens_input=int(tokens_input or 0),
        tokens_output=int(tokens_output or 0),
        total_cost=float(total_cost or 0.0),
    )
