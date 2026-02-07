"""Unit tests for authorization service (no database required)."""

import pytest

from omoi_os.services.authorization_service import AuthorizationService


# Mock database session
class MockDB:
    """Mock database session for unit testing."""

    async def execute(self, *args, **kwargs):
        pass


@pytest.fixture
def auth_service():
    """Create AuthorizationService instance with mock DB."""
    return AuthorizationService(db=MockDB())


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
        assert auth_service._has_permission(permissions, "deeply:nested:permission")

    def test_has_permission_nested_wildcard(self, auth_service):
        """Test nested wildcard permissions."""
        permissions = ["org:members:*"]

        # Should match anything under org:members
        assert auth_service._has_permission(permissions, "org:members:read")
        assert auth_service._has_permission(permissions, "org:members:write")
        assert auth_service._has_permission(permissions, "org:members:delete")

        # Should NOT match parent or sibling permissions
        assert not auth_service._has_permission(permissions, "org:read")
        assert not auth_service._has_permission(permissions, "org:write")
        assert not auth_service._has_permission(permissions, "org:settings:write")

    def test_has_permission_multiple_levels(self, auth_service):
        """Test wildcard at different levels."""
        # Level 1 wildcard
        permissions = ["org:*"]
        assert auth_service._has_permission(permissions, "org:read")
        assert auth_service._has_permission(permissions, "org:write")
        assert auth_service._has_permission(permissions, "org:members:read")
        assert auth_service._has_permission(permissions, "org:members:write")
        assert auth_service._has_permission(permissions, "org:settings:billing:update")

        # Level 2 wildcard
        permissions = ["org:members:*"]
        assert not auth_service._has_permission(permissions, "org:read")
        assert not auth_service._has_permission(permissions, "org:write")
        assert auth_service._has_permission(permissions, "org:members:read")
        assert auth_service._has_permission(permissions, "org:members:write")
        assert not auth_service._has_permission(permissions, "org:settings:read")


class TestPermissionScenarios:
    """Test real-world permission scenarios."""

    def test_owner_permissions(self, auth_service):
        """Test owner role permissions."""
        owner_permissions = [
            "org:*",
            "project:*",
            "document:*",
            "ticket:*",
            "task:*",
            "agent:*",
        ]

        # Should have all permissions
        for action in [
            "org:read",
            "org:write",
            "org:delete",
            "org:members:read",
            "org:members:write",
            "org:members:delete",
            "project:create",
            "project:delete",
            "ticket:assign",
            "task:execute",
            "agent:spawn",
            "agent:terminate",
        ]:
            assert auth_service._has_permission(owner_permissions, action)

    def test_admin_permissions(self, auth_service):
        """Test admin role permissions."""
        admin_permissions = [
            "org:read",
            "org:write",
            "org:members:*",
            "project:*",
            "document:*",
            "ticket:*",
            "task:*",
            "agent:read",
        ]

        # Should have member management
        assert auth_service._has_permission(admin_permissions, "org:members:write")
        assert auth_service._has_permission(admin_permissions, "org:members:delete")

        # Should have project permissions
        assert auth_service._has_permission(admin_permissions, "project:create")
        assert auth_service._has_permission(admin_permissions, "project:delete")

        # Should NOT have org deletion
        assert not auth_service._has_permission(admin_permissions, "org:delete")

        # Can read agents but not manage
        assert auth_service._has_permission(admin_permissions, "agent:read")
        assert not auth_service._has_permission(admin_permissions, "agent:write")
        assert not auth_service._has_permission(admin_permissions, "agent:delete")

    def test_member_permissions(self, auth_service):
        """Test member role permissions."""
        member_permissions = [
            "org:read",
            "project:read",
            "project:write",
            "document:read",
            "document:write",
            "ticket:read",
            "ticket:write",
            "task:read",
            "task:write",
            "agent:read",
        ]

        # Can read and write
        assert auth_service._has_permission(member_permissions, "project:write")
        assert auth_service._has_permission(member_permissions, "ticket:write")

        # Cannot delete or manage
        assert not auth_service._has_permission(member_permissions, "project:delete")
        assert not auth_service._has_permission(member_permissions, "org:write")
        assert not auth_service._has_permission(member_permissions, "org:members:write")

    def test_viewer_permissions(self, auth_service):
        """Test viewer role permissions."""
        viewer_permissions = [
            "org:read",
            "project:read",
            "document:read",
            "ticket:read",
            "task:read",
            "agent:read",
        ]

        # Can read everything
        assert auth_service._has_permission(viewer_permissions, "org:read")
        assert auth_service._has_permission(viewer_permissions, "project:read")

        # Cannot write anything
        assert not auth_service._has_permission(viewer_permissions, "project:write")
        assert not auth_service._has_permission(viewer_permissions, "ticket:write")
        assert not auth_service._has_permission(viewer_permissions, "agent:write")

    def test_agent_executor_permissions(self, auth_service):
        """Test agent executor role permissions."""
        agent_permissions = [
            "project:read",
            "document:read",
            "document:write",
            "ticket:read",
            "ticket:write",
            "task:read",
            "task:write",
            "task:complete:execute",
            "project:git:write",
        ]

        # Can execute tasks
        assert auth_service._has_permission(agent_permissions, "task:complete:execute")

        # Can write code
        assert auth_service._has_permission(agent_permissions, "project:git:write")
        assert auth_service._has_permission(agent_permissions, "document:write")

        # Cannot manage organization
        assert not auth_service._has_permission(agent_permissions, "org:write")
        assert not auth_service._has_permission(agent_permissions, "org:members:write")


class TestComplexPermissions:
    """Test edge cases and complex scenarios."""

    def test_empty_permissions(self, auth_service):
        """Test empty permission list denies everything."""
        permissions = []

        assert not auth_service._has_permission(permissions, "org:read")
        assert not auth_service._has_permission(permissions, "anything")

    def test_permission_specificity(self, auth_service):
        """Test more specific permissions don't override wildcards."""
        permissions = ["org:*", "org:members:read"]

        # Both specific and wildcard should work
        assert auth_service._has_permission(permissions, "org:members:read")
        assert auth_service._has_permission(
            permissions, "org:members:write"
        )  # Via wildcard
        assert auth_service._has_permission(permissions, "org:read")

    def test_multi_level_wildcards(self, auth_service):
        """Test wildcards at different levels don't conflict."""
        permissions = ["org:*", "project:settings:*"]

        # org wildcard
        assert auth_service._has_permission(permissions, "org:anything:here")

        # project settings wildcard
        assert auth_service._has_permission(permissions, "project:settings:read")
        assert auth_service._has_permission(permissions, "project:settings:write")

        # But not other project permissions
        assert not auth_service._has_permission(permissions, "project:read")
        assert not auth_service._has_permission(permissions, "project:delete")

    def test_case_sensitivity(self, auth_service):
        """Test permissions are case-sensitive."""
        permissions = ["org:read"]

        assert auth_service._has_permission(permissions, "org:read")
        # These should NOT match (case sensitive)
        assert not auth_service._has_permission(permissions, "Org:Read")
        assert not auth_service._has_permission(permissions, "ORG:READ")
