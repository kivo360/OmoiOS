"""Tests for /api/v1/projects/{project_id}/settings/spec-driven endpoints.

Run options:
    pytest tests/api/test_spec_driven_settings.py -m unit       # Fast unit tests only
    pytest tests/api/test_spec_driven_settings.py -m integration  # Integration tests (need DB)
    pytest tests/api/test_spec_driven_settings.py               # All tests
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from omoi_os.models.project import Project
from omoi_os.services.database import DatabaseService


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def sample_project(db_service: DatabaseService) -> Project:
    """Create a sample project for testing spec-driven settings."""
    with db_service.get_session() as session:
        project = Project(
            id=f"project-{uuid4()}",
            name=f"Test Project {uuid4().hex[:8]}",
            description="A test project for spec-driven settings",
            status="active",
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.expunge(project)
        return project


@pytest.fixture
def project_with_settings(db_service: DatabaseService) -> Project:
    """Create a project with spec-driven settings already configured."""
    with db_service.get_session() as session:
        project = Project(
            id=f"project-{uuid4()}",
            name=f"Test Project With Settings {uuid4().hex[:8]}",
            description="A test project with existing settings",
            status="active",
            settings={
                "spec_driven": {
                    "enabled": True,
                    "coverage_threshold": 80,
                    "strictness": "medium",
                    "auto_generate_tasks": True,
                    "require_design_approval": True,
                }
            },
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.expunge(project)
        return project


# =============================================================================
# UNIT TESTS (Fast, no database required, uses mocked dependencies)
# =============================================================================


@pytest.mark.unit
@pytest.mark.api
class TestSpecDrivenSettingsValidationUnit:
    """Unit tests for request validation (no auth needed)."""

    def test_get_settings_requires_auth(self, client: TestClient):
        """Test GET /projects/{project_id}/settings/spec-driven requires authentication."""
        fake_id = f"project-{uuid4()}"
        response = client.get(f"/api/v1/projects/{fake_id}/settings/spec-driven")

        # Should return 401 or 403 without authentication
        assert response.status_code in [401, 403]

    def test_patch_settings_requires_auth(self, client: TestClient):
        """Test PATCH /projects/{project_id}/settings/spec-driven requires authentication."""
        fake_id = f"project-{uuid4()}"
        response = client.patch(
            f"/api/v1/projects/{fake_id}/settings/spec-driven",
            json={"coverage_threshold": 80},
        )

        # Should return 401 or 403 without authentication
        assert response.status_code in [401, 403]


@pytest.mark.unit
@pytest.mark.api
class TestSpecDrivenSettingsInputValidationUnit:
    """Unit tests for input validation with mock auth."""

    def test_patch_rejects_invalid_coverage_value_negative(
        self, mock_authenticated_client: TestClient
    ):
        """Test PATCH rejects negative coverage threshold."""
        fake_id = f"project-{uuid4()}"
        response = mock_authenticated_client.patch(
            f"/api/v1/projects/{fake_id}/settings/spec-driven",
            json={"coverage_threshold": -10},
        )

        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422]

    def test_patch_rejects_invalid_coverage_value_over_100(
        self, mock_authenticated_client: TestClient
    ):
        """Test PATCH rejects coverage threshold over 100."""
        fake_id = f"project-{uuid4()}"
        response = mock_authenticated_client.patch(
            f"/api/v1/projects/{fake_id}/settings/spec-driven",
            json={"coverage_threshold": 150},
        )

        # Should return 400 or 422 for validation error
        assert response.status_code in [400, 422]

    def test_patch_rejects_invalid_strictness_enum(
        self, mock_authenticated_client: TestClient
    ):
        """Test PATCH rejects invalid strictness enum value."""
        fake_id = f"project-{uuid4()}"
        response = mock_authenticated_client.patch(
            f"/api/v1/projects/{fake_id}/settings/spec-driven",
            json={"strictness": "invalid_level"},
        )

        # Should return 400 or 422 for invalid enum value
        assert response.status_code in [400, 422]


# =============================================================================
# INTEGRATION TESTS (Slower, requires database, tests real endpoints)
# =============================================================================


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestGetSpecDrivenSettingsIntegration:
    """Integration tests for GET /projects/{project_id}/settings/spec-driven."""

    def test_get_settings_returns_defaults_when_none_exist(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test GET returns default settings when no settings exist."""
        response = authenticated_client.get(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify default values are returned
        assert "enabled" in data
        assert "coverage_threshold" in data
        assert "strictness" in data

    def test_get_settings_returns_saved_settings(
        self, authenticated_client: TestClient, project_with_settings: Project
    ):
        """Test GET returns saved settings."""
        response = authenticated_client.get(
            f"/api/v1/projects/{project_with_settings.id}/settings/spec-driven"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify saved values are returned
        assert data["enabled"] is True
        assert data["coverage_threshold"] == 80
        assert data["strictness"] == "medium"
        assert data["auto_generate_tasks"] is True
        assert data["require_design_approval"] is True

    def test_get_settings_404_for_nonexistent_project(
        self, authenticated_client: TestClient
    ):
        """Test GET returns 404 for non-existent project."""
        fake_id = f"project-{uuid4()}"
        response = authenticated_client.get(
            f"/api/v1/projects/{fake_id}/settings/spec-driven"
        )

        assert response.status_code == 404

    def test_get_settings_403_without_auth(
        self, client: TestClient, sample_project: Project
    ):
        """Test GET returns 401/403 without authentication."""
        response = client.get(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven"
        )

        assert response.status_code in [401, 403]


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestPatchSpecDrivenSettingsIntegration:
    """Integration tests for PATCH /projects/{project_id}/settings/spec-driven."""

    def test_patch_creates_settings_when_none_exist(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test PATCH creates settings when none exist."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={
                "enabled": True,
                "coverage_threshold": 75,
                "strictness": "high",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["enabled"] is True
        assert data["coverage_threshold"] == 75
        assert data["strictness"] == "high"

    def test_patch_updates_existing_settings(
        self, authenticated_client: TestClient, project_with_settings: Project
    ):
        """Test PATCH updates existing settings."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{project_with_settings.id}/settings/spec-driven",
            json={
                "coverage_threshold": 90,
                "strictness": "strict",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["coverage_threshold"] == 90
        assert data["strictness"] == "strict"
        # Other existing settings should remain unchanged
        assert data["enabled"] is True

    def test_patch_partial_update(
        self, authenticated_client: TestClient, project_with_settings: Project
    ):
        """Test PATCH allows partial updates."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{project_with_settings.id}/settings/spec-driven",
            json={"coverage_threshold": 95},
        )

        assert response.status_code == 200
        data = response.json()

        # Updated field
        assert data["coverage_threshold"] == 95
        # Unchanged fields should remain
        assert data["strictness"] == "medium"
        assert data["enabled"] is True

    def test_patch_rejects_invalid_coverage_below_zero(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test PATCH rejects coverage_threshold below 0."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={"coverage_threshold": -5},
        )

        assert response.status_code in [400, 422]

    def test_patch_rejects_invalid_coverage_above_100(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test PATCH rejects coverage_threshold above 100."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={"coverage_threshold": 101},
        )

        assert response.status_code in [400, 422]

    def test_patch_rejects_invalid_strictness(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test PATCH rejects invalid strictness enum value."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={"strictness": "super_strict"},
        )

        assert response.status_code in [400, 422]

    def test_patch_accepts_valid_strictness_values(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test PATCH accepts valid strictness enum values."""
        valid_values = ["low", "medium", "high", "strict"]

        for value in valid_values:
            response = authenticated_client.patch(
                f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
                json={"strictness": value},
            )

            assert response.status_code == 200
            assert response.json()["strictness"] == value

    def test_patch_404_for_nonexistent_project(
        self, authenticated_client: TestClient
    ):
        """Test PATCH returns 404 for non-existent project."""
        fake_id = f"project-{uuid4()}"
        response = authenticated_client.patch(
            f"/api/v1/projects/{fake_id}/settings/spec-driven",
            json={"coverage_threshold": 80},
        )

        assert response.status_code == 404

    def test_patch_403_without_auth(
        self, client: TestClient, sample_project: Project
    ):
        """Test PATCH returns 401/403 without authentication."""
        response = client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={"coverage_threshold": 80},
        )

        assert response.status_code in [401, 403]


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestSpecDrivenSettingsEdgeCasesIntegration:
    """Integration tests for edge cases and boundary conditions."""

    def test_patch_coverage_at_boundary_zero(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test PATCH accepts coverage_threshold of 0."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={"coverage_threshold": 0},
        )

        assert response.status_code == 200
        assert response.json()["coverage_threshold"] == 0

    def test_patch_coverage_at_boundary_100(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test PATCH accepts coverage_threshold of 100."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={"coverage_threshold": 100},
        )

        assert response.status_code == 200
        assert response.json()["coverage_threshold"] == 100

    def test_patch_boolean_fields(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test PATCH handles boolean fields correctly."""
        response = authenticated_client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={
                "enabled": False,
                "auto_generate_tasks": True,
                "require_design_approval": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["enabled"] is False
        assert data["auto_generate_tasks"] is True
        assert data["require_design_approval"] is False

    def test_get_then_patch_consistency(
        self, authenticated_client: TestClient, sample_project: Project
    ):
        """Test that GET after PATCH returns updated values."""
        # First patch some settings
        patch_response = authenticated_client.patch(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven",
            json={
                "enabled": True,
                "coverage_threshold": 85,
                "strictness": "high",
            },
        )
        assert patch_response.status_code == 200

        # Then GET and verify
        get_response = authenticated_client.get(
            f"/api/v1/projects/{sample_project.id}/settings/spec-driven"
        )
        assert get_response.status_code == 200

        data = get_response.json()
        assert data["enabled"] is True
        assert data["coverage_threshold"] == 85
        assert data["strictness"] == "high"

    def test_patch_empty_body(
        self, authenticated_client: TestClient, project_with_settings: Project
    ):
        """Test PATCH with empty body doesn't change settings."""
        # Get original settings
        original = authenticated_client.get(
            f"/api/v1/projects/{project_with_settings.id}/settings/spec-driven"
        ).json()

        # Patch with empty body
        response = authenticated_client.patch(
            f"/api/v1/projects/{project_with_settings.id}/settings/spec-driven",
            json={},
        )

        assert response.status_code == 200
        data = response.json()

        # Settings should remain unchanged
        assert data["coverage_threshold"] == original["coverage_threshold"]
        assert data["strictness"] == original["strictness"]
        assert data["enabled"] == original["enabled"]
