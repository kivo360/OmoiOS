"""Public (unauthenticated) routes for the viral sharing showcase."""

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from omoi_os.api.dependencies import get_db_service, get_current_user
from omoi_os.logging import get_logger
from omoi_os.models.spec import Spec as SpecModel
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ShowcaseStats(BaseModel):
    requirement_count: int
    task_count: int
    tasks_completed: int
    test_coverage: float


class ShowcaseResponse(BaseModel):
    title: str
    description: str | None
    stats: ShowcaseStats
    project_name: str | None
    pull_request_url: str | None
    pull_request_number: int | None
    share_view_count: int


class ShareResponse(BaseModel):
    share_url: str
    share_token: str


# ---------------------------------------------------------------------------
# Public (no auth) – GET showcase page data
# ---------------------------------------------------------------------------


@router.get("/showcase/{share_token}", response_model=ShowcaseResponse)
async def get_showcase(
    share_token: str,
    db: DatabaseService = Depends(get_db_service),
):
    """Return sanitized spec data for the public showcase page.

    No authentication required. Increments view count on each hit.
    """
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel)
            .filter(
                SpecModel.share_token == share_token,
                SpecModel.share_enabled.is_(True),
            )
            .options(
                selectinload(SpecModel.requirements),
                selectinload(SpecModel.tasks),
                selectinload(SpecModel.project),
            )
        )
        spec = result.scalar_one_or_none()

        if not spec:
            raise HTTPException(status_code=404, detail="Showcase not found")

        # Increment view count atomically
        await session.execute(
            select(SpecModel).filter(SpecModel.id == spec.id).with_for_update()
        )
        spec.share_view_count = (spec.share_view_count or 0) + 1
        await session.commit()

        tasks_completed = sum(1 for t in spec.tasks if t.status == "completed")
        project_name = spec.project.name if spec.project else None

        return ShowcaseResponse(
            title=spec.title,
            description=spec.description,
            stats=ShowcaseStats(
                requirement_count=len(spec.requirements),
                task_count=len(spec.tasks),
                tasks_completed=tasks_completed,
                test_coverage=spec.test_coverage or 0.0,
            ),
            project_name=project_name,
            pull_request_url=spec.pull_request_url,
            pull_request_number=spec.pull_request_number,
            share_view_count=spec.share_view_count,
        )


# ---------------------------------------------------------------------------
# Authenticated – POST enable sharing for a spec
# ---------------------------------------------------------------------------


@router.post("/specs/{spec_id}/share", response_model=ShareResponse)
async def enable_spec_sharing(
    spec_id: str,
    db: DatabaseService = Depends(get_db_service),
    current_user: User = Depends(get_current_user),
):
    """Generate a share token and enable public showcase for a spec.

    If sharing is already enabled, returns the existing share URL.
    """
    async with db.get_async_session() as session:
        result = await session.execute(
            select(SpecModel).filter(SpecModel.id == spec_id)
        )
        spec = result.scalar_one_or_none()

        if not spec:
            raise HTTPException(status_code=404, detail="Spec not found")

        # Verify user owns this spec
        if spec.user_id and spec.user_id != current_user.id:
            raise HTTPException(
                status_code=403, detail="Not authorized to share this spec"
            )

        # If already shared, return existing URL
        if spec.share_enabled and spec.share_token:
            return ShareResponse(
                share_url=f"https://omoios.dev/showcase/{spec.share_token}",
                share_token=spec.share_token,
            )

        # Generate token and enable sharing
        token = secrets.token_urlsafe(16)
        spec.share_token = token
        spec.share_enabled = True
        await session.commit()

        logger.info(
            "Sharing enabled for spec",
            spec_id=spec_id,
            share_token=token,
        )

        return ShareResponse(
            share_url=f"https://omoios.dev/showcase/{token}",
            share_token=token,
        )
