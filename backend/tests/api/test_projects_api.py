"""Tests for /api/v1/projects/* endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.api
class TestProjectsEndpointsUnit:
    """Unit tests for project endpoints (using mock authentication)."""

    def test_list_projects(self, mock_authenticated_client: TestClient):
        """Test GET /projects returns list structure."""
        response = mock_authenticated_client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

    def test_list_projects_with_pagination(self, mock_authenticated_client: TestClient):
        """Test GET /projects with limit."""
        response = mock_authenticated_client.get("/api/v1/projects?limit=5")

        assert response.status_code == 200

    def test_get_nonexistent_project(self, mock_authenticated_client: TestClient):
        """Test GET /projects/{id} for non-existent project."""
        fake_id = f"project-{uuid4()}"
        response = mock_authenticated_client.get(f"/api/v1/projects/{fake_id}")

        assert response.status_code == 404

    def test_create_project_validation(self, mock_authenticated_client: TestClient):
        """Test POST /projects validates input."""
        # Empty body should fail validation
        response = mock_authenticated_client.post("/api/v1/projects", json={})

        assert response.status_code == 422

    def test_unauthenticated_access_returns_401(self, client: TestClient):
        """Test that unauthenticated requests return 401."""
        response = client.get("/api/v1/projects")
        assert response.status_code == 401


@pytest.mark.unit
@pytest.mark.api
class TestSpecDrivenSettingsEndpointsUnit:
    """Unit tests for spec-driven settings endpoints."""

    def test_get_spec_driven_settings_nonexistent_project(
        self, mock_authenticated_client: TestClient
    ):
        """Test GET /projects/{id}/settings/spec-driven for non-existent project."""
        fake_id = f"project-{uuid4()}"
        response = mock_authenticated_client.get(
            f"/api/v1/projects/{fake_id}/settings/spec-driven"
        )

        assert response.status_code == 404

    def test_patch_spec_driven_settings_nonexistent_project(
        self, mock_authenticated_client: TestClient
    ):
        """Test PATCH /projects/{id}/settings/spec-driven for non-existent project."""
        fake_id = f"project-{uuid4()}"
        response = mock_authenticated_client.patch(
            f"/api/v1/projects/{fake_id}/settings/spec-driven",
            json={"spec_driven_mode_enabled": True},
        )

        assert response.status_code == 404

    def test_unauthenticated_settings_access_returns_401(self, client: TestClient):
        """Test that unauthenticated requests to settings return 401."""
        fake_id = f"project-{uuid4()}"
        response = client.get(f"/api/v1/projects/{fake_id}/settings/spec-driven")
        assert response.status_code == 401
