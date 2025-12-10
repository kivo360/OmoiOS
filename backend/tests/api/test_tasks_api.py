"""Tests for /api/v1/tasks/* endpoints."""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket


@pytest.mark.unit
@pytest.mark.api
class TestTasksEndpointsUnit:
    """Unit tests for task endpoints."""

    def test_list_tasks(self, client: TestClient):
        """Test GET /tasks returns list."""
        response = client.get("/api/v1/tasks")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_tasks_with_status_filter(self, client: TestClient):
        """Test GET /tasks with status filter."""
        response = client.get("/api/v1/tasks?status=pending")

        assert response.status_code == 200

    def test_list_tasks_with_phase_filter(self, client: TestClient):
        """Test GET /tasks with phase filter."""
        response = client.get("/api/v1/tasks?phase_id=PHASE_REQUIREMENTS")

        assert response.status_code == 200

    def test_list_tasks_with_pagination(self, client: TestClient):
        """Test GET /tasks with limit and offset."""
        response = client.get("/api/v1/tasks?limit=10&offset=0")

        assert response.status_code == 200

    def test_get_nonexistent_task(self, client: TestClient):
        """Test GET /tasks/{id} for non-existent task."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/tasks/{fake_id}")

        assert response.status_code == 404

    def test_get_task_dependencies_nonexistent(self, client: TestClient):
        """Test GET /tasks/{id}/dependencies for non-existent task."""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/tasks/{fake_id}/dependencies")

        assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.api
@pytest.mark.requires_db
class TestTasksCRUDIntegration:
    """Integration tests for task CRUD operations."""

    def test_get_task(self, client: TestClient, sample_task: Task):
        """Test getting a task by ID."""
        response = client.get(f"/api/v1/tasks/{sample_task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(sample_task.id)

    def test_list_tasks_includes_sample(self, client: TestClient, sample_task: Task):
        """Test list includes created task."""
        response = client.get("/api/v1/tasks")

        assert response.status_code == 200
        tasks = response.json()
        task_ids = [t["id"] for t in tasks]
        assert str(sample_task.id) in task_ids

    def test_update_task_status(self, client: TestClient, sample_task: Task):
        """Test updating task status."""
        response = client.patch(
            f"/api/v1/tasks/{sample_task.id}",
            json={"status": "in_progress"},
        )

        # Should succeed or return validation error, not 500
        assert response.status_code in [200, 400, 422]

    def test_get_task_dependencies(self, client: TestClient, sample_task: Task):
        """Test getting task dependencies."""
        response = client.get(f"/api/v1/tasks/{sample_task.id}/dependencies")

        assert response.status_code == 200
        data = response.json()
        assert "depends_on" in data or isinstance(data, list)
