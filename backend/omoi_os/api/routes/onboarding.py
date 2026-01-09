"""Onboarding API routes for tracking user onboarding progress."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from omoi_os.api.dependencies import get_db_session, get_current_user
from omoi_os.logging import get_logger
from omoi_os.models.user import User
from omoi_os.models.user_onboarding import UserOnboarding
from omoi_os.models.organization import Organization, OrganizationMembership
from omoi_os.models.project import Project
from omoi_os.models.subscription import Subscription
from omoi_os.schemas.onboarding import (
    OnboardingStatusResponse,
    OnboardingStepUpdate,
    OnboardingCompleteRequest,
    OnboardingResetRequest,
    OnboardingDetectResponse,
    OnboardingSyncRequest,
    DetectedStepState,
)
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)

router = APIRouter()


async def get_or_create_onboarding(
    db: AsyncSession, user_id: UUID
) -> UserOnboarding:
    """Get existing onboarding record or create a new one."""
    result = await db.execute(
        select(UserOnboarding).where(UserOnboarding.user_id == user_id)
    )
    onboarding = result.scalar_one_or_none()

    if not onboarding:
        onboarding = UserOnboarding(
            id=uuid4(),
            user_id=user_id,
            current_step="welcome",
            completed_steps=[],
            completed_checklist_items=[],
            onboarding_data={},
            sync_version=1,
        )
        db.add(onboarding)
        await db.commit()
        await db.refresh(onboarding)

    return onboarding


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get user's onboarding status.

    Returns current step, completion status, and data.
    Used by frontend to sync state.
    """
    onboarding = await get_or_create_onboarding(db, current_user.id)

    return OnboardingStatusResponse(
        is_completed=onboarding.is_completed,
        current_step=onboarding.current_step,
        completed_steps=onboarding.completed_steps or [],
        completed_checklist_items=onboarding.completed_checklist_items or [],
        completed_at=onboarding.completed_at,
        data=onboarding.onboarding_data or {},
        sync_version=onboarding.sync_version,
    )


@router.post("/step", response_model=OnboardingStatusResponse)
async def update_onboarding_step(
    request: OnboardingStepUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Update user's current onboarding step.

    Called when user progresses through onboarding.
    """
    onboarding = await get_or_create_onboarding(db, current_user.id)

    # Update step
    old_step = onboarding.current_step
    onboarding.current_step = request.step

    # Add old step to completed if not already there
    completed_steps = list(onboarding.completed_steps or [])
    if old_step not in completed_steps:
        completed_steps.append(old_step)
    onboarding.completed_steps = completed_steps

    # Also mark as checklist item complete
    completed_checklist = list(onboarding.completed_checklist_items or [])
    if old_step not in completed_checklist:
        completed_checklist.append(old_step)
    onboarding.completed_checklist_items = completed_checklist

    # Merge data
    existing_data = onboarding.onboarding_data or {}
    existing_data.update(request.data)
    onboarding.onboarding_data = existing_data

    # Increment sync version
    onboarding.sync_version += 1
    onboarding.updated_at = utc_now()

    await db.commit()
    await db.refresh(onboarding)

    logger.info(
        f"User {current_user.id} progressed from step '{old_step}' to '{request.step}'"
    )

    return OnboardingStatusResponse(
        is_completed=onboarding.is_completed,
        current_step=onboarding.current_step,
        completed_steps=onboarding.completed_steps or [],
        completed_checklist_items=onboarding.completed_checklist_items or [],
        completed_at=onboarding.completed_at,
        data=onboarding.onboarding_data or {},
        sync_version=onboarding.sync_version,
    )


@router.post("/complete", response_model=OnboardingStatusResponse)
async def complete_onboarding(
    request: OnboardingCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Mark onboarding as complete.

    Sets completed_at timestamp.
    """
    onboarding = await get_or_create_onboarding(db, current_user.id)

    # Mark as complete
    onboarding.completed_at = utc_now()
    onboarding.current_step = "complete"

    # Add 'complete' to completed steps
    completed_steps = list(onboarding.completed_steps or [])
    if "complete" not in completed_steps:
        completed_steps.append("complete")
    onboarding.completed_steps = completed_steps

    # Merge final data
    existing_data = onboarding.onboarding_data or {}
    existing_data.update(request.data)
    onboarding.onboarding_data = existing_data

    # Increment sync version
    onboarding.sync_version += 1
    onboarding.updated_at = utc_now()

    await db.commit()
    await db.refresh(onboarding)

    logger.info(f"User {current_user.id} completed onboarding")

    return OnboardingStatusResponse(
        is_completed=onboarding.is_completed,
        current_step=onboarding.current_step,
        completed_steps=onboarding.completed_steps or [],
        completed_checklist_items=onboarding.completed_checklist_items or [],
        completed_at=onboarding.completed_at,
        data=onboarding.onboarding_data or {},
        sync_version=onboarding.sync_version,
    )


@router.post("/reset", response_model=OnboardingStatusResponse)
async def reset_onboarding(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    admin_override: bool = Query(False),
):
    """
    Reset onboarding to beginning.

    Requires admin role OR debug mode enabled.
    For regular users, this is typically only available in dev/staging.
    """
    # In production, only allow admins to reset
    # For now, allow anyone in development
    # TODO: Add proper environment check

    onboarding = await get_or_create_onboarding(db, current_user.id)

    # Reset all fields
    onboarding.current_step = "welcome"
    onboarding.completed_steps = []
    onboarding.completed_checklist_items = []
    onboarding.completed_at = None
    onboarding.onboarding_data = {}
    onboarding.sync_version += 1
    onboarding.updated_at = utc_now()

    await db.commit()
    await db.refresh(onboarding)

    logger.info(f"User {current_user.id} reset their onboarding")

    return OnboardingStatusResponse(
        is_completed=onboarding.is_completed,
        current_step=onboarding.current_step,
        completed_steps=onboarding.completed_steps or [],
        completed_checklist_items=onboarding.completed_checklist_items or [],
        completed_at=onboarding.completed_at,
        data=onboarding.onboarding_data or {},
        sync_version=onboarding.sync_version,
    )


@router.get("/detect", response_model=OnboardingDetectResponse)
async def detect_onboarding_state(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Auto-detect user's current state for onboarding steps.

    Returns what the user has already completed with their current values.
    This allows returning users to see their existing setup and change if needed.
    """
    # Check GitHub connection from user attributes
    github_connected = bool(
        current_user.attributes
        and current_user.attributes.get("github_access_token")
    )
    github_username = (
        current_user.attributes.get("github_username")
        if current_user.attributes
        else None
    )

    # Check organizations
    result = await db.execute(
        select(Organization)
        .join(OrganizationMembership)
        .where(OrganizationMembership.user_id == current_user.id)
    )
    orgs = result.scalars().all()

    # Check projects with GitHub repos
    org_ids = [org.id for org in orgs]
    projects = []
    if org_ids:
        result = await db.execute(
            select(Project).where(
                Project.organization_id.in_(org_ids),
                Project.github_repo.isnot(None),
            )
        )
        projects = result.scalars().all()

    # Check subscription
    subscription = None
    if org_ids:
        result = await db.execute(
            select(Subscription).where(
                Subscription.organization_id.in_(org_ids),
                Subscription.status.in_(["active", "trialing"]),
            )
        )
        subscription = result.scalar_one_or_none()

    # Build detected state
    github_state = DetectedStepState(
        completed=github_connected,
        current={"username": github_username} if github_username else None,
        can_change=True,
    )

    organization_state = DetectedStepState(
        completed=len(orgs) > 0,
        current={
            "id": str(orgs[0].id),
            "name": orgs[0].name,
        }
        if orgs
        else None,
        can_change=True,
    )

    repo_state = DetectedStepState(
        completed=len(projects) > 0,
        current={
            "owner": projects[0].github_owner,
            "name": projects[0].github_repo,
            "project_id": str(projects[0].id),
        }
        if projects
        else None,
        can_change=True,
    )

    plan_state = DetectedStepState(
        completed=subscription is not None,
        current={
            "plan": subscription.tier if subscription else None,
            "status": subscription.status if subscription else None,
        }
        if subscription
        else None,
        can_change=True,
    )

    # Determine suggested starting step
    suggested_step = _determine_start_step(
        github_connected, orgs, projects, subscription
    )

    return OnboardingDetectResponse(
        github=github_state,
        organization=organization_state,
        repo=repo_state,
        plan=plan_state,
        suggested_step=suggested_step,
    )


def _determine_start_step(
    github_connected: bool,
    orgs: list,
    projects: list,
    subscription,
) -> str:
    """Determine which onboarding step user should start at."""
    if not github_connected:
        return "github"
    if not orgs:
        return "welcome"  # Will create org implicitly
    if not projects:
        return "repo"
    if not subscription:
        return "plan"
    return "complete"


@router.post("/sync", response_model=OnboardingStatusResponse)
async def sync_onboarding_state(
    request: OnboardingSyncRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Sync onboarding state from client to server.

    Used for bi-directional sync. Server version takes precedence
    if sync_version is higher.
    """
    onboarding = await get_or_create_onboarding(db, current_user.id)

    # Server version takes precedence if higher
    if onboarding.sync_version > request.local_sync_version:
        logger.info(
            f"Server version ({onboarding.sync_version}) > client ({request.local_sync_version}), "
            f"returning server state"
        )
        return OnboardingStatusResponse(
            is_completed=onboarding.is_completed,
            current_step=onboarding.current_step,
            completed_steps=onboarding.completed_steps or [],
            completed_checklist_items=onboarding.completed_checklist_items or [],
            completed_at=onboarding.completed_at,
            data=onboarding.onboarding_data or {},
            sync_version=onboarding.sync_version,
        )

    # Client version is newer or equal, update server
    onboarding.current_step = request.current_step
    onboarding.completed_steps = request.completed_steps
    onboarding.completed_checklist_items = request.completed_checklist_items

    # Merge data (don't overwrite, merge)
    existing_data = onboarding.onboarding_data or {}
    existing_data.update(request.data)
    onboarding.onboarding_data = existing_data

    # Increment sync version
    onboarding.sync_version = request.local_sync_version + 1
    onboarding.updated_at = utc_now()

    await db.commit()
    await db.refresh(onboarding)

    logger.info(
        f"Synced onboarding state for user {current_user.id}, "
        f"new version: {onboarding.sync_version}"
    )

    return OnboardingStatusResponse(
        is_completed=onboarding.is_completed,
        current_step=onboarding.current_step,
        completed_steps=onboarding.completed_steps or [],
        completed_checklist_items=onboarding.completed_checklist_items or [],
        completed_at=onboarding.completed_at,
        data=onboarding.onboarding_data or {},
        sync_version=onboarding.sync_version,
    )


# Admin endpoint for resetting any user's onboarding
@router.post("/admin/reset/{user_id}", response_model=OnboardingStatusResponse)
async def admin_reset_onboarding(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Admin endpoint to reset a user's onboarding.

    Requires super admin role.
    """
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can reset other users' onboarding",
        )

    # Get or create onboarding for target user
    result = await db.execute(
        select(UserOnboarding).where(UserOnboarding.user_id == user_id)
    )
    onboarding = result.scalar_one_or_none()

    if not onboarding:
        # Check if user exists
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        onboarding = UserOnboarding(
            id=uuid4(),
            user_id=user_id,
            current_step="welcome",
            completed_steps=[],
            completed_checklist_items=[],
            onboarding_data={},
            sync_version=1,
        )
        db.add(onboarding)
    else:
        # Reset existing
        onboarding.current_step = "welcome"
        onboarding.completed_steps = []
        onboarding.completed_checklist_items = []
        onboarding.completed_at = None
        onboarding.onboarding_data = {}
        onboarding.sync_version += 1
        onboarding.updated_at = utc_now()

    await db.commit()
    await db.refresh(onboarding)

    logger.info(
        f"Admin {current_user.id} reset onboarding for user {user_id}"
    )

    return OnboardingStatusResponse(
        is_completed=onboarding.is_completed,
        current_step=onboarding.current_step,
        completed_steps=onboarding.completed_steps or [],
        completed_checklist_items=onboarding.completed_checklist_items or [],
        completed_at=onboarding.completed_at,
        data=onboarding.onboarding_data or {},
        sync_version=onboarding.sync_version,
    )
