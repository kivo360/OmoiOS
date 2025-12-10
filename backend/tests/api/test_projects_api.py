"""Tests for /api/v1/projects/* endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


@pytest.mark.unit
@pytest.mark.api
class TestProjectsEndpointsUnit:
    """Unit tests for project endpoints."""

    def test_list_projects(self, client: TestClient):
        """Test GET /projects returns list structure."""
        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

    def test_list_projects_with_pagination(self, client: TestClient):
        """Test GET /projects with limit."""
        response = client.get("/api/v1/projects?limit=5")

        assert response.status_code == 200

    def test_get_nonexistent_project(self, client: TestClient):
        """Test GET /projects/{id} for non-existent project."""
        fake_id = f"project-{uuid4()}"
        response = client.get(f"/api/v1/projects/{fake_id}")

        assert response.status_code == 404

    def test_create_project_validation(self, client: TestClient):
        """Test POST /projects validates input."""
        # Empty body should fail validation
        response = client.post("/api/v1/projects", json={})

        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestProjectsCRUDIntegration:
    """Integration tests for project CRUD."""

    def test_create_project(self, client: TestClient):
        """Test creating a new project."""
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "Test Project",
                "description": "A test project",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert "id" in data

    def test_get_project(self, client: TestClient):
        """Test getting a project by ID."""
        # First create a project
        create_response = client.post(
            "/api/v1/projects",
            json={"name": "Get Test Project"},
        )
        project_id = create_response.json()["id"]

        # Now get it
        response = client.get(f"/api/v1/projects/{project_id}")

        assert response.status_code == 200
        assert response.json()["name"] == "Get Test Project"

    def test_list_projects_includes_created(self, client: TestClient):
        """Test list includes created project."""
        # Create project
        client.post("/api/v1/projects", json={"name": "List Test Project"})

        # List and check
        response = client.get("/api/v1/projects")

        assert response.status_code == 200
        projects = response.json()["projects"]
        names = [p["name"] for p in projects]
        assert "List Test Project" in names
