"""Tests for resource monitoring API routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from omoi_os.api.routes.resources import router
from omoi_os.models.sandbox_resource import SandboxResource
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_sandbox_resource():
    """Create a mock SandboxResource."""
    return SandboxResource(
        id=str(uuid4()),
        sandbox_id="sb-test-123",
        task_id="task-456",
        agent_id="agent-789",
        allocated_cpu_cores=2,
        allocated_memory_gb=4,
        allocated_disk_gb=8,
        cpu_usage_percent=50.0,
        memory_usage_percent=60.0,
        memory_used_mb=2400.0,
        disk_usage_percent=30.0,
        disk_used_gb=2.4,
        status="running",
        last_updated=utc_now(),
        created_at=utc_now(),
    )


class TestResourcesAPI:
    """Tests for resources API endpoints."""

    def test_get_sandbox_resources_empty(self, client):
        """Test getting sandbox resources when none exist."""
        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_active_sandboxes = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.get("/api/v1/resources/sandboxes")

            assert response.status_code == 200
            assert response.json() == []

    def test_get_sandbox_resources_with_data(self, client, mock_sandbox_resource):
        """Test getting sandbox resources with data."""
        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_active_sandboxes = AsyncMock(
                return_value=[mock_sandbox_resource]
            )
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.get("/api/v1/resources/sandboxes")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["sandbox_id"] == "sb-test-123"
            assert data[0]["allocation"]["cpu_cores"] == 2
            assert data[0]["usage"]["cpu_usage_percent"] == 50.0

    def test_get_sandbox_resource_not_found(self, client):
        """Test getting a non-existent sandbox resource."""
        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_sandbox = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.get("/api/v1/resources/sandboxes/nonexistent")

            assert response.status_code == 404

    def test_get_sandbox_resource_found(self, client, mock_sandbox_resource):
        """Test getting an existing sandbox resource."""
        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_sandbox = AsyncMock(return_value=mock_sandbox_resource)
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.get("/api/v1/resources/sandboxes/sb-test-123")

            assert response.status_code == 200
            data = response.json()
            assert data["sandbox_id"] == "sb-test-123"

    def test_update_sandbox_allocation_not_found(self, client):
        """Test updating allocation for non-existent sandbox."""
        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_sandbox = AsyncMock(return_value=None)
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.post(
                    "/api/v1/resources/sandboxes/nonexistent/allocate",
                    json={"cpu_cores": 4},
                )

            assert response.status_code == 404

    def test_update_sandbox_allocation_no_fields(self, client, mock_sandbox_resource):
        """Test updating allocation without any fields."""
        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_sandbox = AsyncMock(return_value=mock_sandbox_resource)
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.post(
                    "/api/v1/resources/sandboxes/sb-test-123/allocate",
                    json={},
                )

            assert response.status_code == 400

    def test_update_sandbox_allocation_success(self, client, mock_sandbox_resource):
        """Test successful allocation update."""
        updated_resource = SandboxResource(
            id=mock_sandbox_resource.id,
            sandbox_id="sb-test-123",
            task_id="task-456",
            agent_id="agent-789",
            allocated_cpu_cores=4,  # Updated
            allocated_memory_gb=8,  # Updated
            allocated_disk_gb=8,
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
            memory_used_mb=2400.0,
            disk_usage_percent=30.0,
            disk_used_gb=2.4,
            status="running",
            last_updated=utc_now(),
            created_at=utc_now(),
        )

        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_sandbox = AsyncMock(return_value=mock_sandbox_resource)
            mock_service.update_allocation = AsyncMock(return_value=updated_resource)
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.post(
                    "/api/v1/resources/sandboxes/sb-test-123/allocate",
                    json={"cpu_cores": 4, "memory_gb": 8},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["allocation"]["cpu_cores"] == 4
            assert data["allocation"]["memory_gb"] == 8

    def test_get_resource_summary(self, client):
        """Test getting resource summary."""
        mock_summary = {
            "total_sandboxes": 3,
            "total_cpu_allocated": 6,
            "total_memory_allocated_gb": 12,
            "total_disk_allocated_gb": 24,
            "avg_cpu_usage_percent": 45.5,
            "avg_memory_usage_percent": 60.2,
            "avg_disk_usage_percent": 30.0,
        }

        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_resource_summary = AsyncMock(return_value=mock_summary)
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.get("/api/v1/resources/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["total_sandboxes"] == 3
            assert data["avg_cpu_usage_percent"] == 45.5

    def test_get_metrics_history(self, client):
        """Test getting metrics history."""
        with patch(
            "omoi_os.api.routes.resources.ResourceMonitorService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.get_metrics_history = AsyncMock(return_value=[])
            mock_service_class.return_value = mock_service

            with patch("omoi_os.api.routes.resources.get_db_service"):
                response = client.get(
                    "/api/v1/resources/sandboxes/sb-test-123/history?hours=1"
                )

            assert response.status_code == 200
            assert response.json() == []
