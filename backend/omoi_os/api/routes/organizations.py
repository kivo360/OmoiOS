"""Organization API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List
from uuid import UUID

from omoi_os.api.dependencies import (
    get_db_session,
    get_current_user,
    get_authorization_service,
    require_permission,
)
from omoi_os.models.user import User
from omoi_os.models.organization import Organization, OrganizationMembership, Role
from omoi_os.schemas.organization import (
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    OrganizationSummary,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    MembershipCreate,
    MembershipResponse,
    MembershipUpdate,
    InviteMemberRequest,
)
from omoi_os.services.authorization_service import AuthorizationService, ActorType

router = APIRouter()


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: OrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Create a new organization.
    
    The current user becomes the owner with full permissions.
    """
    # Check if slug already exists
    result = await db.execute(
        select(Organization).where(Organization.slug == request.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists"
        )

    # Create organization
    org = Organization(
        name=request.name,
        slug=request.slug,
        description=request.description,
        owner_id=current_user.id,
        billing_email=request.billing_email,
        is_active=True
    )

    db.add(org)
    await db.flush()

    # Get owner role
    owner_role_result = await db.execute(
        select(Role).where(
            Role.name == "owner",
            Role.is_system == True,
            Role.organization_id.is_(None)
        )
    )
    owner_role = owner_role_result.scalar_one()

    # Create membership for owner
    membership = OrganizationMembership(
        user_id=current_user.id,
        organization_id=org.id,
        role_id=owner_role.id
    )

    db.add(membership)
    await db.commit()
    await db.refresh(org)

    return OrganizationResponse.model_validate(org)


@router.get("", response_model=List[OrganizationSummary])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """List all organizations the current user is a member of."""
    orgs = await auth_service.get_user_organizations(current_user.id)

    return [
        OrganizationSummary(
            id=org["organization_id"],
            name=org["organization_name"],
            slug=org["organization_slug"],
            role=org["role"]
        )
        for org in orgs
    ]


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """Get organization details."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:read",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return OrganizationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: UUID,
    request: OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """Update organization."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:write",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Update organization
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.billing_email is not None:
        update_data["billing_email"] = request.billing_email
    if request.settings is not None:
        update_data["settings"] = request.settings
    if request.max_concurrent_agents is not None:
        update_data["max_concurrent_agents"] = request.max_concurrent_agents
    if request.max_agent_runtime_hours is not None:
        update_data["max_agent_runtime_hours"] = request.max_agent_runtime_hours

    if update_data:
        await db.execute(
            update(Organization)
            .where(Organization.id == org_id)
            .values(**update_data)
        )
        await db.commit()

    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one()

    return OrganizationResponse.model_validate(org)


@router.delete("/{org_id}")
async def delete_organization(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """
    Delete (archive) organization.
    
    Only owner can delete. This is a soft delete.
    """
    # Check if user is owner
    is_owner = await auth_service.is_organization_owner(current_user.id, org_id)

    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owner can delete organization"
        )

    # Soft delete
    await db.execute(
        update(Organization)
        .where(Organization.id == org_id)
        .values(is_active=False)
    )
    await db.commit()

    return {"message": "Organization archived successfully"}


# Member management

@router.post("/{org_id}/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: UUID,
    request: MembershipCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """Add a member to organization."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:members:write",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Verify role exists
    role_result = await db.execute(
        select(Role).where(Role.id == request.role_id)
    )
    if not role_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Create membership
    membership = OrganizationMembership(
        user_id=request.user_id,
        agent_id=request.agent_id,
        organization_id=org_id,
        role_id=request.role_id,
        invited_by=current_user.id
    )

    db.add(membership)
    await db.commit()
    await db.refresh(membership)

    # Load role for response
    role = await db.execute(
        select(Role).where(Role.id == membership.role_id)
    )
    role_obj = role.scalar_one()

    response = MembershipResponse.model_validate(membership)
    response.role_name = role_obj.name

    return response


@router.get("/{org_id}/members", response_model=List[MembershipResponse])
async def list_members(
    org_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """List organization members."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:members:read",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.organization_id == org_id)
        .options(selectinload(OrganizationMembership.role))
    )
    memberships = result.scalars().all()

    return [
        MembershipResponse(
            id=m.id,
            user_id=m.user_id,
            agent_id=m.agent_id,
            organization_id=m.organization_id,
            role_id=m.role_id,
            role_name=m.role.name,
            joined_at=m.joined_at
        )
        for m in memberships
    ]


@router.patch("/{org_id}/members/{member_id}", response_model=MembershipResponse)
async def update_member(
    org_id: UUID,
    member_id: UUID,
    request: MembershipUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """Update member role."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:members:write",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Update membership
    await db.execute(
        update(OrganizationMembership)
        .where(
            OrganizationMembership.id == member_id,
            OrganizationMembership.organization_id == org_id
        )
        .values(role_id=request.role_id)
    )
    await db.commit()

    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.id == member_id)
        .options(selectinload(OrganizationMembership.role))
    )
    membership = result.scalar_one()

    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        agent_id=membership.agent_id,
        organization_id=membership.organization_id,
        role_id=membership.role_id,
        role_name=membership.role.name,
        joined_at=membership.joined_at
    )


@router.delete("/{org_id}/members/{member_id}")
async def remove_member(
    org_id: UUID,
    member_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """Remove member from organization."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:members:delete",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Delete membership
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.id == member_id,
            OrganizationMembership.organization_id == org_id
        )
    )
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    await db.delete(membership)
    await db.commit()

    return {"message": "Member removed successfully"}


# Role management

@router.get("/{org_id}/roles", response_model=List[RoleResponse])
async def list_roles(
    org_id: UUID,
    include_system: bool = True,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """List roles available in organization."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:read",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Get org-specific roles
    query = select(Role).where(Role.organization_id == org_id)

    # Include system roles if requested
    if include_system:
        query = select(Role).where(
            (Role.organization_id == org_id) | (Role.is_system == True)
        )

    result = await db.execute(query)
    roles = result.scalars().all()

    return [RoleResponse.model_validate(role) for role in roles]


@router.post("/{org_id}/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    org_id: UUID,
    request: RoleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """Create custom role for organization."""
    # Check permission (admin only)
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:write",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Create role
    role = Role(
        organization_id=org_id,
        name=request.name,
        description=request.description,
        permissions=request.permissions,
        is_system=False,
        inherits_from=request.inherits_from
    )

    db.add(role)
    await db.commit()
    await db.refresh(role)

    return RoleResponse.model_validate(role)


@router.patch("/{org_id}/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    org_id: UUID,
    role_id: UUID,
    request: RoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """Update custom role (cannot update system roles)."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:write",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Get role
    result = await db.execute(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == org_id
        )
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify system roles"
        )

    # Update role
    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.description is not None:
        update_data["description"] = request.description
    if request.permissions is not None:
        update_data["permissions"] = request.permissions
    if request.inherits_from is not None:
        update_data["inherits_from"] = request.inherits_from

    if update_data:
        await db.execute(
            update(Role)
            .where(Role.id == role_id)
            .values(**update_data)
        )
        await db.commit()

        result = await db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = result.scalar_one()

    return RoleResponse.model_validate(role)


@router.delete("/{org_id}/roles/{role_id}")
async def delete_role(
    org_id: UUID,
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    auth_service: AuthorizationService = Depends(get_authorization_service)
):
    """Delete custom role (cannot delete system roles)."""
    # Check permission
    allowed, reason, _ = await auth_service.is_authorized(
        actor_id=current_user.id,
        actor_type=ActorType.USER,
        action="org:write",
        organization_id=org_id
    )

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=reason
        )

    # Get role
    result = await db.execute(
        select(Role).where(
            Role.id == role_id,
            Role.organization_id == org_id
        )
    )
    role = result.scalar_one_or_none()

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete system roles"
        )

    await db.delete(role)
    await db.commit()

    return {"message": "Role deleted successfully"}

