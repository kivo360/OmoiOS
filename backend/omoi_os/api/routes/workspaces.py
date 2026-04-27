"""Workspace API routes (tenant-level resource per agent-platform-spec §02)."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from omoi_os.api.dependencies import (
    get_auth_context,
    get_authorization_service,
    get_db_session,
)
from omoi_os.models.organization import OrganizationMembership
from omoi_os.models.user import User
from omoi_os.models.workspace import Workspace
from omoi_os.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from omoi_os.services.authorization_service import ActorType, AuthorizationService

router = APIRouter()


async def _resolve_default_org(db: AsyncSession, user: User) -> Optional[UUID]:
    """Pick the first org the user is a member of. Used when the caller hasn't
    provided `organization_id` and the API key isn't org-scoped."""
    result = await db.execute(
        select(OrganizationMembership.organization_id)
        .where(OrganizationMembership.user_id == user.id)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def _assert_org_member(
    auth: AuthorizationService, user: User, org_id: UUID, action: str
) -> None:
    allowed, reason, _ = await auth.is_authorized(
        actor_id=user.id,
        actor_type=ActorType.USER,
        action=action,
        organization_id=org_id,
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)


async def _user_org_ids(db: AsyncSession, user: User) -> List[UUID]:
    result = await db.execute(
        select(OrganizationMembership.organization_id).where(
            OrganizationMembership.user_id == user.id
        )
    )
    return [row[0] for row in result.all()]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: WorkspaceCreate,
    auth_ctx: tuple[User, Optional[UUID]] = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service),
):
    """Create a workspace.

    The organization is resolved in this order:
      1. `request.organization_id` (if provided and caller is a member)
      2. The API key's bound organization (if present)
      3. The caller's first-owned organization (fallback for JWT callers)
    """
    user, key_org_id = auth_ctx

    org_id = request.organization_id or key_org_id
    if org_id is None:
        org_id = await _resolve_default_org(db, user)
    if org_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No organization resolvable; pass organization_id or create one first",
        )

    await _assert_org_member(auth_service, user, org_id, "org:write")

    # Slug collision inside the org
    existing = await db.execute(
        select(Workspace).where(
            Workspace.organization_id == org_id, Workspace.slug == request.slug
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace slug '{request.slug}' already exists in this organization",
        )

    ws = Workspace(
        organization_id=org_id,
        name=request.name,
        slug=request.slug,
        default_environment_id=request.default_environment_id,
        settings=request.settings or {},
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)

    return WorkspaceResponse.model_validate(ws)


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    organization_id: Optional[UUID] = Query(
        None, description="Filter by a specific organization the caller is a member of"
    ),
    include_inactive: bool = Query(False),
    auth_ctx: tuple[User, Optional[UUID]] = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
):
    """List workspaces visible to the caller.

    If `organization_id` is given, lists workspaces in that org (caller must be
    a member). Otherwise, lists workspaces across every org the caller is a
    member of. API-key callers see only their key's org when one is bound.
    """
    user, key_org_id = auth_ctx

    if organization_id is not None:
        member_org_ids = await _user_org_ids(db, user)
        if organization_id not in member_org_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization",
            )
        scope_ids = [organization_id]
    elif key_org_id is not None:
        scope_ids = [key_org_id]
    else:
        scope_ids = await _user_org_ids(db, user)

    if not scope_ids:
        return []

    query = select(Workspace).where(Workspace.organization_id.in_(scope_ids))
    if not include_inactive:
        query = query.where(Workspace.is_active.is_(True))
    query = query.order_by(Workspace.created_at.asc())

    result = await db.execute(query)
    return [WorkspaceResponse.model_validate(ws) for ws in result.scalars().all()]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: UUID,
    auth_ctx: tuple[User, Optional[UUID]] = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    user, _ = auth_ctx
    await _assert_org_member(auth_service, user, ws.organization_id, "org:read")

    return WorkspaceResponse.model_validate(ws)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: UUID,
    request: WorkspaceUpdate,
    auth_ctx: tuple[User, Optional[UUID]] = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    user, _ = auth_ctx
    await _assert_org_member(auth_service, user, ws.organization_id, "org:write")

    updates: dict = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.default_environment_id is not None:
        updates["default_environment_id"] = request.default_environment_id
    if request.settings is not None:
        updates["settings"] = request.settings
    if request.is_active is not None:
        updates["is_active"] = request.is_active

    if updates:
        await db.execute(
            update(Workspace).where(Workspace.id == workspace_id).values(**updates)
        )
        await db.commit()
        result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
        ws = result.scalar_one()

    return WorkspaceResponse.model_validate(ws)


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    workspace_id: UUID,
    auth_ctx: tuple[User, Optional[UUID]] = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service),
):
    """Soft-delete (archive) the workspace."""
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found"
        )

    user, _ = auth_ctx
    await _assert_org_member(auth_service, user, ws.organization_id, "org:write")

    await db.execute(
        update(Workspace).where(Workspace.id == workspace_id).values(is_active=False)
    )
    await db.commit()
    return None
