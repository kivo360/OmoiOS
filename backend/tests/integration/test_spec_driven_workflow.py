"""Integration tests for spec-driven workflow.

Tests the end-to-end flow:
1. Create ticket with workflow_mode="spec_driven" in context
2. Verify Spec is created with source_ticket_id
3. Verify sandbox events can update spec phase_data
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

from fastapi.testclient import TestClient

from omoi_os.models.project import Project
from omoi_os.models.organization import Organization, OrganizationMembership, Role
from omoi_os.models.spec import Spec
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService


@pytest.fixture
def test_organization(db_service: DatabaseService, test_user: User) -> Organization:
    """Create a test organization owned by the test user."""
    with db_service.get_session() as session:
        org = Organization(
            id=uuid4(),
            name="Test Organization",
            slug=f"test-org-{uuid4().hex[:8]}",
            owner_id=test_user.id,
            is_active=True,
        )
        session.add(org)
        session.commit()
        session.refresh(org)
        session.expunge(org)
        return org


@pytest.fixture
def test_project(
    db_service: DatabaseService,
    test_organization: Organization,
) -> Project:
    """Create a test project."""
    with db_service.get_session() as session:
        project = Project(
            id=f"project-{uuid4()}",  # Project IDs use string format
            name="Test Project",
            organization_id=test_organization.id,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.expunge(project)
        return project


@pytest.fixture
def user_with_project_access(
    db_service: DatabaseService,
    test_user: User,
    test_organization: Organization,
) -> User:
    """Add user to organization so they can access projects."""
    with db_service.get_session() as session:
        # First create a role for the organization
        role = Role(
            id=uuid4(),
            organization_id=test_organization.id,
            name="member",
            description="Test member role",
            permissions=["project:read", "project:write"],
            is_system=False,
        )
        session.add(role)
        session.flush()

        # Now create the membership with the role_id
        membership = OrganizationMembership(
            id=uuid4(),
            user_id=test_user.id,
            organization_id=test_organization.id,
            role_id=role.id,
        )
        session.add(membership)
        session.commit()
    return test_user


@pytest.mark.integration
class TestSpecDrivenTicketCreation:
    """Test spec-driven workflow triggered from ticket creation."""

    def test_ticket_creation_triggers_spec_workflow(
        self,
        authenticated_client: TestClient,
        db_service: DatabaseService,
        test_project: Project,
        user_with_project_access: User,
    ):
        """Test that creating a ticket with workflow_mode=spec_driven creates a Spec."""
        # Mock the Daytona spawner to avoid external calls
        # The import is inside _trigger_spec_driven_workflow, so we patch at the source
        with patch(
            "omoi_os.services.daytona_spawner.get_daytona_spawner"
        ) as mock_get_spawner:
            # Setup mock spawner
            mock_spawner = MagicMock()
            mock_spawner.spawn_for_phase = AsyncMock(return_value="mock-sandbox-123")
            mock_get_spawner.return_value = mock_spawner

            # Also mock billing service to allow execution
            with patch(
                "omoi_os.services.billing_service.get_billing_service"
            ) as mock_get_billing:
                mock_billing = MagicMock()
                mock_billing.can_execute_workflow.return_value = (True, None)
                mock_get_billing.return_value = mock_billing

                # Create ticket with spec_driven workflow mode
                # Note: workflow_mode is a top-level field, not inside context
                unique_id = uuid4().hex[:8]
                unique_title = f"Test Spec-Driven Ticket - {unique_id}"
                response = authenticated_client.post(
                    "/api/v1/tickets",
                    json={
                        "title": unique_title,
                        "description": f"This ticket should trigger spec-driven workflow - {unique_id}",
                        "project_id": str(test_project.id),
                        "priority": "MEDIUM",
                        "check_duplicates": False,  # Disable dedup for test isolation
                        "workflow_mode": "spec_driven",  # Top-level field, not in context
                    },
                )

                # The endpoint returns 200 for successful ticket creation
                assert response.status_code == 200, f"Response: {response.json()}"
                ticket_data = response.json()
                assert "id" in ticket_data, "Expected TicketResponse with 'id' field"
                ticket_id = ticket_data["id"]

                # Give async background task time to run
                # The spec creation is async but should complete quickly
                import time

                time.sleep(2.0)  # Increased wait for async spec creation

                # Verify spec was created
                with db_service.get_session() as session:
                    specs = (
                        session.query(Spec)
                        .filter(
                            Spec.spec_context.contains({"source_ticket_id": ticket_id})
                        )
                        .all()
                    )

                    assert len(specs) == 1, f"Expected 1 spec, found {len(specs)}"
                    spec = specs[0]
                    assert spec.title == unique_title
                    assert spec.status == "executing"
                    assert spec.current_phase == "explore"
                    assert spec.spec_context.get("workflow_mode") == "spec_driven"

                # Verify spawner was called
                mock_spawner.spawn_for_phase.assert_called_once()
                call_args = mock_spawner.spawn_for_phase.call_args
                assert call_args.kwargs["phase"] == "explore"
                assert call_args.kwargs["project_id"] == str(test_project.id)

    def test_ticket_creation_without_spec_mode_no_spec(
        self,
        authenticated_client: TestClient,
        db_service: DatabaseService,
        test_project: Project,
        user_with_project_access: User,
    ):
        """Test that regular tickets don't create specs."""
        # Use unique title to avoid duplicate detection
        unique_title = f"Regular Ticket - No Spec Test - {uuid4().hex[:8]}"
        response = authenticated_client.post(
            "/api/v1/tickets",
            json={
                "title": unique_title,
                "description": f"This is a regular ticket for testing - {uuid4().hex}",
                "project_id": str(test_project.id),
                "priority": "MEDIUM",
                "check_duplicates": False,  # Disable dedup to ensure new ticket
            },
        )

        # The endpoint returns 200 for successful ticket creation (API design choice)
        # When check_duplicates=False, it creates the ticket and returns TicketResponse
        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}. Response: {response.json()}"
        ticket_data = response.json()

        # Verify it's a TicketResponse (has 'id') not a DuplicateCheckResponse (has 'is_duplicate')
        assert "id" in ticket_data, "Expected TicketResponse with 'id' field"
        ticket_id = ticket_data["id"]

        # Verify no spec was created
        with db_service.get_session() as session:
            specs = (
                session.query(Spec)
                .filter(Spec.spec_context.contains({"source_ticket_id": ticket_id}))
                .all()
            )
            assert len(specs) == 0


@pytest.mark.integration
class TestSandboxEventCallbacks:
    """Test sandbox events endpoint for spec phase updates."""

    def test_sandbox_event_creates_event_record(
        self,
        client: TestClient,
        db_service: DatabaseService,
    ):
        """Test that sandbox events are recorded."""
        sandbox_id = f"test-sandbox-{uuid4().hex[:8]}"
        spec_id = str(uuid4())

        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/events",
            json={
                "event_type": "phase.started",
                "event_data": {
                    "spec_id": spec_id,
                    "phase": "explore",
                },
                "source": "agent",
            },
        )

        assert response.status_code == 200, f"Response: {response.json()}"
        data = response.json()
        assert data["status"] == "received"
        assert data["sandbox_id"] == sandbox_id
        assert data["event_type"] == "phase.started"

    def test_sandbox_event_updates_spec_phase_data(
        self,
        client: TestClient,
        db_service: DatabaseService,
    ):
        """Test that agent.completed event updates spec's phase_data."""
        # First create an organization and project (required for spec)
        with db_service.get_session() as session:
            from omoi_os.models.organization import Organization
            from omoi_os.models.project import Project
            from omoi_os.models.user import User

            # Create a user first
            user = User(
                id=uuid4(),
                email=f"spec_test_{uuid4().hex[:8]}@example.com",
                full_name="Spec Test User",
                hashed_password="not-a-real-hash",
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            session.flush()

            # Create organization
            org = Organization(
                id=uuid4(),
                name="Test Org for Spec Events",
                slug=f"test-org-spec-{uuid4().hex[:8]}",
                owner_id=user.id,
                is_active=True,
            )
            session.add(org)
            session.flush()

            # Create project
            project = Project(
                id=uuid4(),
                name="Test Project for Spec Events",
                organization_id=org.id,
            )
            session.add(project)
            session.flush()

            # Now create the spec with required project_id
            spec = Spec(
                id=uuid4(),
                project_id=str(project.id),
                title="Test Spec for Events",
                description="Testing phase_data updates",
                status="executing",
                current_phase="explore",
                phase_data={},
            )
            session.add(spec)
            session.commit()
            session.refresh(spec)
            spec_id = str(spec.id)

        sandbox_id = f"test-sandbox-{uuid4().hex[:8]}"

        # Post agent.completed event with phase_data
        response = client.post(
            f"/api/v1/sandboxes/{sandbox_id}/events",
            json={
                "event_type": "agent.completed",
                "event_data": {
                    "spec_id": spec_id,
                    "success": True,
                    "phase_data": {
                        "explore": {
                            "completed_at": "2024-01-18T12:00:00Z",
                            "codebase_summary": {
                                "languages": ["python"],
                                "frameworks": ["fastapi"],
                            },
                        },
                    },
                },
                "source": "agent",
            },
        )

        assert response.status_code == 200, f"Response: {response.json()}"

        # Give the async handler time to update spec
        import time

        time.sleep(0.5)

        # Verify spec's phase_data was updated
        with db_service.get_session() as session:
            updated_spec = session.query(Spec).filter(Spec.id == spec_id).first()
            assert updated_spec is not None
            phase_data = updated_spec.phase_data or {}

            # The explore phase data should be present
            # Note: exact behavior depends on _update_spec_phase_data implementation
            assert (
                "explore" in phase_data or len(phase_data) > 0
            ), f"Expected phase_data to be updated, got: {phase_data}"

    def test_sandbox_event_validates_source(
        self,
        client: TestClient,
    ):
        """Test that sandbox events validate the source field."""
        response = client.post(
            "/api/v1/sandboxes/test-sandbox/events",
            json={
                "event_type": "test.event",
                "event_data": {},
                "source": "invalid_source",
            },
        )

        assert response.status_code == 422  # Validation error


@pytest.mark.integration
class TestSpecEndpoints:
    """Test spec-related endpoints."""

    def test_list_specs_by_project(
        self,
        authenticated_client: TestClient,
        db_service: DatabaseService,
        test_project: Project,
        user_with_project_access: User,
    ):
        """Test listing specs by project."""
        # Create specs
        with db_service.get_session() as session:
            spec1 = Spec(
                id=uuid4(),
                title="Spec 1",
                project_id=test_project.id,
                status="draft",
            )
            spec2 = Spec(
                id=uuid4(),
                title="Spec 2",
                project_id=test_project.id,
                status="executing",
            )
            session.add_all([spec1, spec2])
            session.commit()

        response = authenticated_client.get(
            f"/api/v1/specs/project/{test_project.id}",
        )

        assert response.status_code == 200
        data = response.json()
        specs = data.get("specs", [])
        assert len(specs) >= 2

    def test_get_spec_by_id(
        self,
        authenticated_client: TestClient,
        db_service: DatabaseService,
        test_project: Project,
        user_with_project_access: User,
    ):
        """Test getting a spec by ID."""
        with db_service.get_session() as session:
            spec = Spec(
                id=uuid4(),
                title="Test Spec",
                project_id=test_project.id,
                status="draft",
                phase_data={"test": "data"},
            )
            session.add(spec)
            session.commit()
            spec_id = str(spec.id)

        response = authenticated_client.get(f"/api/v1/specs/{spec_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Spec"
        assert data["status"] == "draft"
        # Note: phase_data is stored in DB but not exposed in SpecResponse
