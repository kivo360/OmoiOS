"""Tests for AuthorizationService."""

import pytest
import pytest_asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from omoi_os.models.user import User
from omoi_os.models.organization import Organization, OrganizationMembership, Role
from omoi_os.services.authorization_service import AuthorizationService, ActorType

# Test database setup
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def async_engine():
    """Create async test database engine."""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    async with engine.begin() as conn:
        # Only create tables needed for authorization testing
        await conn.run_sync(User.__table__.create, checkfirst=True)
        await conn.run_sync(Organization.__table__.create, checkfirst=True)
        await conn.run_sync(Role.__table__.create, checkfirst=True)
        await conn.run_sync(OrganizationMembership.__table__.create, checkfirst=True)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine):
    """Create async database session."""
    async_session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def auth_service(db_session):
    """Create AuthorizationService instance."""
    return AuthorizationService(db=db_session)


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed",
        full_name="Test User",
        is_active=True,
        is_verified=True,
        is_super_admin=False,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def super_admin_user(db_session):
    """Create super admin user."""
    user = User(
        email="admin@example.com",
        hashed_password="hashed",
        full_name="Super Admin",
        is_active=True,
        is_verified=True,
        is_super_admin=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def test_organization(db_session, test_user):
    """Create test organization."""
    org = Organization(
        name="Test Organization", slug="test-org", owner_id=test_user.id, is_active=True
    )

    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)

    return org


@pytest_asyncio.fixture
async def owner_role(db_session):
    """Create owner role."""
    role = Role(
        name="owner",
        description="Owner role",
        permissions=["org:*", "project:*"],
        is_system=True,
    )

    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    return role


@pytest_asyncio.fixture
async def member_role(db_session):
    """Create member role."""
    role = Role(
        name="member",
        description="Member role",
        permissions=["org:read", "project:read", "project:write"],
        is_system=True,
    )

    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    return role


@pytest_asyncio.fixture
async def viewer_role(db_session):
    """Create viewer role."""
    role = Role(
        name="viewer",
        description="Viewer role",
        permissions=["org:read", "project:read"],
        is_system=True,
    )

    db_session.add(role)
    await db_session.commit()
    await db_session.refresh(role)

    return role


class TestPermissionChecking:
    """Test permission checking logic."""

    def test_has_permission_direct_match(self, auth_service):
        """Test direct permission match."""
        permissions = ["org:read", "project:write"]

        assert auth_service._has_permission(permissions, "org:read")
        assert auth_service._has_permission(permissions, "project:write")
        assert not auth_service._has_permission(permissions, "org:write")

    def test_has_permission_wildcard(self, auth_service):
        """Test wildcard permission matching."""
        permissions = ["org:*", "project:read"]

        # Wildcard should match everything under org
        assert auth_service._has_permission(permissions, "org:read")
        assert auth_service._has_permission(permissions, "org:write")
        assert auth_service._has_permission(permissions, "org:delete")
        assert auth_service._has_permission(permissions, "org:members:write")

        # Non-wildcard should only match exact
        assert auth_service._has_permission(permissions, "project:read")
        assert not auth_service._has_permission(permissions, "project:write")

    def test_has_permission_super_wildcard(self, auth_service):
        """Test super wildcard (*:*)."""
        permissions = ["*:*"]

        assert auth_service._has_permission(permissions, "org:read")
        assert auth_service._has_permission(permissions, "project:write")
        assert auth_service._has_permission(permissions, "anything:anywhere")

    def test_has_permission_nested_wildcard(self, auth_service):
        """Test nested wildcard permissions."""
        permissions = ["org:members:*"]

        assert auth_service._has_permission(permissions, "org:members:read")
        assert auth_service._has_permission(permissions, "org:members:write")
        assert auth_service._has_permission(permissions, "org:members:delete")
        assert not auth_service._has_permission(permissions, "org:read")
        assert not auth_service._has_permission(permissions, "org:write")


class TestSuperAdminAuthorization:
    """Test super admin bypass."""

    @pytest.mark.asyncio
    async def test_super_admin_bypasses_checks(
        self, auth_service, super_admin_user, test_organization
    ):
        """Test super admin bypasses all permission checks."""
        allowed, reason, details = await auth_service.is_authorized(
            actor_id=super_admin_user.id,
            actor_type=ActorType.USER,
            action="anything:write",
            organization_id=test_organization.id,
        )

        assert allowed
        assert "super admin" in reason.lower()
        assert "super_admin" in details["evaluation_order"]

    @pytest.mark.asyncio
    async def test_agent_cannot_be_super_admin(self, auth_service, test_organization):
        """Test agents cannot use super admin bypass."""
        agent_id = uuid4()

        # Even if we try to authorize as super admin, agents can't use it
        allowed, reason, details = await auth_service.is_authorized(
            actor_id=agent_id,
            actor_type=ActorType.AGENT,
            action="org:delete",
            organization_id=test_organization.id,
        )

        assert not allowed
        assert "super_admin" not in details["evaluation_order"]


class TestRBACAuthorization:
    """Test RBAC permission checking."""

    @pytest.mark.asyncio
    async def test_user_with_owner_role(
        self, auth_service, db_session, test_user, test_organization, owner_role
    ):
        """Test user with owner role has all permissions."""
        # Add user to org with owner role
        membership = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=owner_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Check various permissions
        for action in [
            "org:read",
            "org:write",
            "org:delete",
            "project:write",
            "project:delete",
        ]:
            allowed, reason, details = await auth_service.is_authorized(
                actor_id=test_user.id,
                actor_type=ActorType.USER,
                action=action,
                organization_id=test_organization.id,
            )

            assert allowed, f"Owner should have permission: {action}"
            assert "owner" in details["matched_roles"]

    @pytest.mark.asyncio
    async def test_user_with_member_role(
        self, auth_service, db_session, test_user, test_organization, member_role
    ):
        """Test user with member role has limited permissions."""
        # Add user to org with member role
        membership = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=member_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Should have read/write permissions
        allowed, _, _ = await auth_service.is_authorized(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            action="org:read",
            organization_id=test_organization.id,
        )
        assert allowed

        allowed, _, _ = await auth_service.is_authorized(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            action="project:write",
            organization_id=test_organization.id,
        )
        assert allowed

        # Should NOT have delete permissions
        allowed, _, _ = await auth_service.is_authorized(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            action="org:delete",
            organization_id=test_organization.id,
        )
        assert not allowed

    @pytest.mark.asyncio
    async def test_user_with_viewer_role(
        self, auth_service, db_session, test_user, test_organization, viewer_role
    ):
        """Test user with viewer role has read-only access."""
        # Add user to org with viewer role
        membership = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=viewer_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Should have read permissions
        allowed, _, _ = await auth_service.is_authorized(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            action="org:read",
            organization_id=test_organization.id,
        )
        assert allowed

        # Should NOT have write permissions
        allowed, _, _ = await auth_service.is_authorized(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            action="org:write",
            organization_id=test_organization.id,
        )
        assert not allowed


class TestOrganizationMembershipChecks:
    """Test organization membership checking."""

    @pytest.mark.asyncio
    async def test_is_organization_member(
        self, auth_service, db_session, test_user, test_organization, member_role
    ):
        """Test checking if user is org member."""
        # Not a member initially
        is_member = await auth_service.is_organization_member(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            organization_id=test_organization.id,
        )
        assert not is_member

        # Add membership
        membership = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=member_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Should be member now
        is_member = await auth_service.is_organization_member(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            organization_id=test_organization.id,
        )
        assert is_member

    @pytest.mark.asyncio
    async def test_is_organization_owner(
        self, auth_service, db_session, test_user, test_organization
    ):
        """Test checking if user is org owner."""
        # test_user is the owner (from fixture)
        is_owner = await auth_service.is_organization_owner(
            user_id=test_user.id, organization_id=test_organization.id
        )
        assert is_owner

        # Create another user who is not owner
        other_user = User(
            email="other@example.com", hashed_password="hashed", is_active=True
        )
        db_session.add(other_user)
        await db_session.commit()
        await db_session.refresh(other_user)

        is_owner = await auth_service.is_organization_owner(
            user_id=other_user.id, organization_id=test_organization.id
        )
        assert not is_owner


class TestGetUserOrganizations:
    """Test getting user's organizations."""

    @pytest.mark.asyncio
    async def test_get_user_organizations(
        self, auth_service, db_session, test_user, test_organization, member_role
    ):
        """Test retrieving user's organizations."""
        # Add membership
        membership = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=member_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Get organizations
        orgs = await auth_service.get_user_organizations(test_user.id)

        assert len(orgs) == 1
        assert orgs[0]["organization_name"] == "Test Organization"
        assert orgs[0]["organization_slug"] == "test-org"
        assert orgs[0]["role"] == "member"
        assert "org:read" in orgs[0]["permissions"]

    @pytest.mark.asyncio
    async def test_get_user_multiple_organizations(
        self,
        auth_service,
        db_session,
        test_user,
        test_organization,
        owner_role,
        member_role,
    ):
        """Test user in multiple organizations."""
        # Create second org
        org2 = Organization(
            name="Second Org", slug="second-org", owner_id=test_user.id, is_active=True
        )
        db_session.add(org2)
        await db_session.flush()

        # Add memberships
        membership1 = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=member_role.id,
        )
        membership2 = OrganizationMembership(
            user_id=test_user.id, organization_id=org2.id, role_id=owner_role.id
        )
        db_session.add_all([membership1, membership2])
        await db_session.commit()

        # Get organizations
        orgs = await auth_service.get_user_organizations(test_user.id)

        assert len(orgs) == 2
        org_names = {org["organization_name"] for org in orgs}
        assert "Test Organization" in org_names
        assert "Second Org" in org_names


class TestGetUserPermissions:
    """Test getting all user permissions."""

    @pytest.mark.asyncio
    async def test_get_user_permissions(
        self, auth_service, db_session, test_user, test_organization, member_role
    ):
        """Test retrieving user's permissions."""
        # Add membership
        membership = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=member_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Get permissions
        permissions = await auth_service.get_user_permissions(
            user_id=test_user.id, organization_id=test_organization.id
        )

        assert "org:read" in permissions
        assert "project:read" in permissions
        assert "project:write" in permissions

    @pytest.mark.asyncio
    async def test_get_permissions_with_inheritance(
        self, auth_service, db_session, test_user, test_organization
    ):
        """Test permission inheritance from parent roles."""
        # Create parent role
        parent_role = Role(
            name="parent",
            permissions=["project:read"],
            is_system=False,
            organization_id=test_organization.id,
        )
        db_session.add(parent_role)
        await db_session.flush()

        # Create child role that inherits
        child_role = Role(
            name="child",
            permissions=["org:read"],
            is_system=False,
            organization_id=test_organization.id,
            inherits_from=parent_role.id,
        )
        db_session.add(child_role)
        await db_session.flush()

        # Add membership with child role
        membership = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=child_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Get permissions - should include both child and parent
        permissions = await auth_service.get_user_permissions(
            user_id=test_user.id, organization_id=test_organization.id
        )

        assert "org:read" in permissions  # From child
        assert "project:read" in permissions  # From parent


class TestAuthorizationFlow:
    """Test complete authorization flows."""

    @pytest.mark.asyncio
    async def test_unauthorized_user(self, auth_service, test_user, test_organization):
        """Test user without membership is unauthorized."""
        allowed, reason, details = await auth_service.is_authorized(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            action="org:read",
            organization_id=test_organization.id,
        )

        assert not allowed
        assert "No matching authorization" in reason
        assert len(details["matched_roles"]) == 0

    @pytest.mark.asyncio
    async def test_authorized_user(
        self, auth_service, db_session, test_user, test_organization, member_role
    ):
        """Test authorized user can perform allowed actions."""
        # Add membership
        membership = OrganizationMembership(
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=member_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Check allowed action
        allowed, reason, details = await auth_service.is_authorized(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            action="org:read",
            organization_id=test_organization.id,
        )

        assert allowed
        assert "member" in details["matched_roles"]
        assert "org_role" in details["evaluation_order"]

    @pytest.mark.asyncio
    async def test_evaluation_order(
        self, auth_service, db_session, super_admin_user, test_organization, owner_role
    ):
        """Test super admin is checked before RBAC."""
        # Give super admin a membership too
        membership = OrganizationMembership(
            user_id=super_admin_user.id,
            organization_id=test_organization.id,
            role_id=owner_role.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Should hit super admin first
        allowed, reason, details = await auth_service.is_authorized(
            actor_id=super_admin_user.id,
            actor_type=ActorType.USER,
            action="org:write",
            organization_id=test_organization.id,
        )

        assert allowed
        assert details["evaluation_order"][0] == "super_admin"
        # Should not need to check RBAC
        assert len(details["matched_roles"]) == 0


class TestRoleHierarchy:
    """Test role inheritance."""

    @pytest.mark.asyncio
    async def test_role_inheritance(
        self, auth_service, db_session, test_user, test_organization
    ):
        """Test permissions are inherited from parent roles."""
        # Create role hierarchy: grandparent -> parent -> child
        grandparent = Role(
            name="grandparent",
            permissions=["level3:read"],
            is_system=False,
            organization_id=test_organization.id,
        )
        db_session.add(grandparent)
        await db_session.flush()

        parent = Role(
            name="parent",
            permissions=["level2:read"],
            is_system=False,
            organization_id=test_organization.id,
            inherits_from=grandparent.id,
        )
        db_session.add(parent)
        await db_session.flush()

        child = Role(
            name="child",
            permissions=["level1:read"],
            is_system=False,
            organization_id=test_organization.id,
            inherits_from=parent.id,
        )
        db_session.add(child)
        await db_session.flush()

        # Add user with child role
        membership = OrganizationMembership(
            user_id=test_user.id, organization_id=test_organization.id, role_id=child.id
        )
        db_session.add(membership)
        await db_session.commit()

        # Should have access via inheritance
        allowed, _, details = await auth_service.is_authorized(
            actor_id=test_user.id,
            actor_type=ActorType.USER,
            action="level3:read",
            organization_id=test_organization.id,
        )

        assert allowed
        # Should show full role chain
        assert "child" in details["matched_roles"]
        assert "parent" in details["matched_roles"]
        assert "grandparent" in details["matched_roles"]
