"""Integration tests for preview API routes.

Tests the preview REST API endpoints with mocked database operations.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from omoi_os.models.preview_session import PreviewSession, PreviewStatus

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = str(uuid4())
    user.email = "test@example.com"
    user.role = "admin"
    user.deleted_at = None
    user.waitlist_status = "approved"
    user.attributes = {}
    return user


def _make_preview_session(
    sandbox_id="sb-test-123",
    task_id=None,
    project_id=None,
    status=PreviewStatus.PENDING.value,
    preview_url=None,
    port=3000,
    framework="vite",
) -> MagicMock:
    """Create a mock PreviewSession matching the Pydantic response model."""
    preview = MagicMock(spec=PreviewSession)
    preview.id = str(uuid4())
    preview.sandbox_id = sandbox_id
    preview.task_id = task_id
    preview.project_id = project_id
    preview.status = status
    preview.preview_url = preview_url
    preview.port = port
    preview.framework = framework
    preview.error_message = None
    preview.created_at = datetime.now(timezone.utc)
    preview.ready_at = None
    preview.stopped_at = None
    return preview


@pytest.fixture
def app(mock_user):
    """Create a FastAPI test app with mocked dependencies."""
    from omoi_os.api.routes.preview import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/preview")

    # Override auth dependency to return mock user
    from omoi_os.api.dependencies import (
        get_current_user,
        get_db_service,
        get_event_bus_service,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db_service] = lambda: MagicMock()
    app.dependency_overrides[get_event_bus_service] = lambda: MagicMock()

    return app


@pytest.fixture
def client(app):
    """Create a TestClient."""
    return TestClient(app)


# ============================================================================
# Tests: POST /api/v1/preview/
# ============================================================================


class TestCreatePreviewRoute:
    """Tests for POST /api/v1/preview/."""

    def test_create_preview_returns_201(self, client, app):
        """Test creating a preview returns 201 with preview data."""
        preview = _make_preview_session(sandbox_id="sb-new")

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.create_preview = AsyncMock(return_value=preview)

            response = client.post(
                "/api/v1/preview/",
                json={"sandbox_id": "sb-new", "port": 3000, "framework": "vite"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["sandbox_id"] == "sb-new"
        assert data["status"] == "pending"
        assert data["port"] == 3000

    def test_create_duplicate_sandbox_returns_409(self, client, app):
        """Test creating a duplicate preview returns 409 Conflict."""
        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.create_preview = AsyncMock(
                side_effect=ValueError("Preview already exists for sandbox sb-dup")
            )

            response = client.post(
                "/api/v1/preview/",
                json={"sandbox_id": "sb-dup"},
            )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


# ============================================================================
# Tests: GET /api/v1/preview/{preview_id}
# ============================================================================


class TestGetPreviewRoute:
    """Tests for GET /api/v1/preview/{preview_id}."""

    def test_get_preview_returns_status(self, client, app):
        """Test getting preview returns full details."""
        preview = _make_preview_session(
            sandbox_id="sb-get",
            status=PreviewStatus.READY.value,
            preview_url="https://preview.example.com",
        )

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_id = AsyncMock(return_value=preview)

            response = client.get(f"/api/v1/preview/{preview.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["preview_url"] == "https://preview.example.com"

    def test_get_preview_not_found(self, client, app):
        """Test getting non-existent preview returns 404."""
        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_id = AsyncMock(return_value=None)

            response = client.get("/api/v1/preview/nonexistent-id")

        assert response.status_code == 404


# ============================================================================
# Tests: DELETE /api/v1/preview/{preview_id}
# ============================================================================


class TestStopPreviewRoute:
    """Tests for DELETE /api/v1/preview/{preview_id}."""

    def test_delete_preview_stops(self, client, app):
        """Test deleting a preview transitions to STOPPED."""
        preview = _make_preview_session(
            status=PreviewStatus.STOPPED.value,
        )

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.mark_stopped = AsyncMock(return_value=preview)

            response = client.delete(f"/api/v1/preview/{preview.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "stopped"

    def test_delete_preview_not_found(self, client, app):
        """Test deleting non-existent preview returns 404."""
        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.mark_stopped = AsyncMock(
                side_effect=ValueError("Preview not found")
            )

            response = client.delete("/api/v1/preview/nonexistent-id")

        assert response.status_code == 404


# ============================================================================
# Tests: GET /api/v1/preview/sandbox/{sandbox_id}
# ============================================================================


class TestGetPreviewBySandboxRoute:
    """Tests for GET /api/v1/preview/sandbox/{sandbox_id}."""

    def test_get_preview_by_sandbox(self, client, app):
        """Test sandbox lookup returns preview data."""
        preview = _make_preview_session(sandbox_id="sb-lookup")

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=preview)

            response = client.get("/api/v1/preview/sandbox/sb-lookup")

        assert response.status_code == 200
        data = response.json()
        assert data["sandbox_id"] == "sb-lookup"

    def test_get_preview_by_sandbox_not_found(self, client, app):
        """Test sandbox lookup returns 404 when no preview exists."""
        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=None)

            response = client.get("/api/v1/preview/sandbox/sb-missing")

        assert response.status_code == 404
