"""Authorization service for RBAC and permission checking."""

from typing import Optional, Dict, Tuple, List
from uuid import UUID
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from omoi_os.models.user import User
from omoi_os.models.organization import Organization, OrganizationMembership, Role


class ActorType(str, Enum):
    """Type of actor (user or agent)."""
    USER = "user"
    AGENT = "agent"


class AuthorizationService:
    """Service for authorization and permission checking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_authorized(
        self,
        actor_id: UUID,
        actor_type: ActorType,
        action: str,
        organization_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
    ) -> Tuple[bool, str, Dict]:
        """
        Check if actor is authorized to perform action.
        
        Priority order:
        1. Super admin (users only)
        2. Organization role (RBAC)
        3. Explicit deny (future: ABAC policies)
        
        Args:
            actor_id: UUID of user or agent
            actor_type: ActorType.USER or ActorType.AGENT
            action: Permission string (e.g., "project:read", "ticket:write")
            organization_id: Organization context
            resource_type: Optional resource type
            resource_id: Optional specific resource ID
        
        Returns:
            Tuple of (allowed, reason, details)
            - allowed: bool - whether action is permitted
            - reason: str - human-readable explanation
            - details: dict - matched roles, evaluation order
        """
        details = {
            "matched_roles": [],
            "evaluation_order": [],
            "actor_type": actor_type.value
        }

        # 1. Check super admin (users only)
        if actor_type == ActorType.USER:
            user_result = await self.db.execute(
                select(User).where(User.id == actor_id)
            )
            user = user_result.scalar_one_or_none()

            if user and user.is_super_admin:
                details["evaluation_order"].append("super_admin")
                return True, "Authorized as super admin", details

        # 2. Check organization role (RBAC)
        rbac_check = await self._check_org_rbac(
            actor_id, actor_type, organization_id, action
        )

        if rbac_check["allowed"]:
            details["matched_roles"] = rbac_check["roles"]
            details["evaluation_order"].append("org_role")
            return True, f"Authorized via role: {', '.join(rbac_check['roles'])}", details

        # 3. Future: Check ABAC policies
        # 4. Future: Check explicit deny policies

        return False, "No matching authorization found", details

    async def _check_org_rbac(
        self,
        actor_id: UUID,
        actor_type: ActorType,
        organization_id: UUID,
        action: str
    ) -> Dict:
        """Check organization-level RBAC permissions."""
        # Build query based on actor type
        if actor_type == ActorType.USER:
            query = (
                select(OrganizationMembership)
                .where(
                    OrganizationMembership.user_id == actor_id,
                    OrganizationMembership.organization_id == organization_id
                )
                .options(selectinload(OrganizationMembership.role))
            )
        else:  # AGENT
            query = (
                select(OrganizationMembership)
                .where(
                    OrganizationMembership.agent_id == actor_id,
                    OrganizationMembership.organization_id == organization_id
                )
                .options(selectinload(OrganizationMembership.role))
            )

        result = await self.db.execute(query)
        membership = result.scalar_one_or_none()

        if not membership:
            return {"allowed": False, "roles": []}

        role = membership.role

        # Check if role has permission (with inheritance)
        if self._has_permission(role.permissions, action):
            return {"allowed": True, "roles": [role.name]}

        # Check parent roles
        if role.inherits_from:
            # Load parent role
            parent_result = await self.db.execute(
                select(Role).where(Role.id == role.inherits_from)
            )
            parent_role = parent_result.scalar_one_or_none()

            if parent_role:
                parent_check = await self._check_role_hierarchy(parent_role, action)
                if parent_check["allowed"]:
                    return {
                        "allowed": True,
                        "roles": [role.name] + parent_check["roles"]
                    }

        return {"allowed": False, "roles": []}

    async def _check_role_hierarchy(self, role: Role, action: str) -> Dict:
        """Recursively check parent roles."""
        if self._has_permission(role.permissions, action):
            return {"allowed": True, "roles": [role.name]}

        if role.inherits_from:
            parent_result = await self.db.execute(
                select(Role).where(Role.id == role.inherits_from)
            )
            parent_role = parent_result.scalar_one_or_none()

            if parent_role:
                parent_check = await self._check_role_hierarchy(parent_role, action)
                if parent_check["allowed"]:
                    return {
                        "allowed": True,
                        "roles": [role.name] + parent_check["roles"]
                    }

        return {"allowed": False, "roles": []}

    def _has_permission(self, permissions: List[str], required: str) -> bool:
        """
        Check if permission list contains required permission (with wildcards).
        
        Examples:
            permissions=["org:*"], required="org:read" → True
            permissions=["project:read"], required="project:write" → False
            permissions=["*:*"], required="anything" → True
        """
        # Direct match
        if required in permissions:
            return True

        # Super wildcard
        if "*:*" in permissions:
            return True

        # Check wildcards
        parts = required.split(":")
        for i in range(len(parts)):
            wildcard = ":".join(parts[:i + 1]) + ":*"
            if wildcard in permissions:
                return True

        return False

    async def get_user_permissions(
        self,
        user_id: UUID,
        organization_id: UUID
    ) -> List[str]:
        """Get all permissions for user in organization."""
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id
            )
            .options(selectinload(OrganizationMembership.role))
        )
        membership = result.scalar_one_or_none()

        if not membership:
            return []

        # Get role permissions (including inherited)
        all_permissions = list(membership.role.permissions)

        # Add inherited permissions
        if membership.role.inherits_from:
            parent_result = await self.db.execute(
                select(Role).where(Role.id == membership.role.inherits_from)
            )
            parent_role = parent_result.scalar_one_or_none()

            if parent_role:
                all_permissions.extend(parent_role.permissions)

        return list(set(all_permissions))  # Remove duplicates

    async def is_organization_member(
        self,
        actor_id: UUID,
        actor_type: ActorType,
        organization_id: UUID
    ) -> bool:
        """Check if actor is a member of organization."""
        if actor_type == ActorType.USER:
            query = select(OrganizationMembership).where(
                OrganizationMembership.user_id == actor_id,
                OrganizationMembership.organization_id == organization_id
            )
        else:
            query = select(OrganizationMembership).where(
                OrganizationMembership.agent_id == actor_id,
                OrganizationMembership.organization_id == organization_id
            )

        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def is_organization_owner(
        self,
        user_id: UUID,
        organization_id: UUID
    ) -> bool:
        """Check if user is organization owner."""
        result = await self.db.execute(
            select(Organization).where(
                Organization.id == organization_id,
                Organization.owner_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_user_organizations(
        self,
        user_id: UUID
    ) -> List[Dict]:
        """Get all organizations user is a member of."""
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(OrganizationMembership.user_id == user_id)
            .options(
                selectinload(OrganizationMembership.organization),
                selectinload(OrganizationMembership.role)
            )
        )
        memberships = result.scalars().all()

        return [
            {
                "organization_id": str(membership.organization.id),
                "organization_name": membership.organization.name,
                "organization_slug": membership.organization.slug,
                "role": membership.role.name,
                "permissions": membership.role.permissions,
                "joined_at": membership.joined_at
            }
            for membership in memberships
        ]

