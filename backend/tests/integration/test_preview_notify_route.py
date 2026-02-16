"""Integration tests for POST /api/v1/preview/notify endpoint.

Tests the worker callback endpoint for preview status transitions.
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


def _make_preview_session(
    sandbox_id="sb-test-123",
    status=PreviewStatus.PENDING.value,
    preview_url=None,
    preview_token=None,
) -> MagicMock:
    """Create a mock PreviewSession."""
    preview = MagicMock(spec=PreviewSession)
    preview.id = str(uuid4())
    preview.sandbox_id = sandbox_id
    preview.status = status
    preview.preview_url = preview_url
    preview.preview_token = preview_token
    preview.task_id = "task-123"
    preview.project_id = None
    preview.port = 3000
    preview.framework = "vite"
    preview.error_message = None
    preview.created_at = datetime.now(timezone.utc)
    preview.ready_at = None
    preview.stopped_at = None
    return preview


@pytest.fixture
def app():
    """Create a FastAPI test app with mocked dependencies.

    The /notify endpoint does NOT require authentication,
    so we don't need to mock get_current_user.
    """
    from omoi_os.api.routes.preview import router
    from fastapi import FastAPI
    from omoi_os.api.dependencies import get_db_service, get_event_bus_service

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/preview")

    app.dependency_overrides[get_db_service] = lambda: MagicMock()
    app.dependency_overrides[get_event_bus_service] = lambda: MagicMock()

    return app


@pytest.fixture
def client(app):
    """Create a TestClient."""
    return TestClient(app)


# ============================================================================
# Tests: POST /api/v1/preview/notify — status transitions
# ============================================================================


class TestNotifyStarting:
    """Tests for notify with status=starting."""

    def test_notify_starting_calls_mark_starting(self, client):
        """Starting status should call mark_starting on the manager."""
        preview = _make_preview_session(sandbox_id="sb-start")

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=preview)
            instance.mark_starting = AsyncMock()

            response = client.post(
                "/api/v1/preview/notify",
                json={"sandbox_id": "sb-start", "status": "starting"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["preview_id"] == preview.id
        instance.mark_starting.assert_awaited_once_with(preview.id)


class TestNotifyReady:
    """Tests for notify with status=ready."""

    def test_notify_ready_uses_prestored_url(self, client):
        """Ready status should use pre-stored URL from spawner."""
        preview = _make_preview_session(
            sandbox_id="sb-ready",
            preview_url="https://pre-stored.daytona.io/preview",
            preview_token="tok-pre",
        )

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=preview)
            instance.mark_ready = AsyncMock()

            response = client.post(
                "/api/v1/preview/notify",
                json={"sandbox_id": "sb-ready", "status": "ready"},
            )

        assert response.status_code == 200
        instance.mark_ready.assert_awaited_once_with(
            preview.id,
            "https://pre-stored.daytona.io/preview",
            "tok-pre",
        )

    def test_notify_ready_worker_url_overrides(self, client):
        """Worker-provided URL should override pre-stored URL."""
        preview = _make_preview_session(
            sandbox_id="sb-override",
            preview_url="https://pre-stored.example.com",
            preview_token="tok-old",
        )

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=preview)
            instance.mark_ready = AsyncMock()

            response = client.post(
                "/api/v1/preview/notify",
                json={
                    "sandbox_id": "sb-override",
                    "status": "ready",
                    "preview_url": "https://worker-provided.example.com",
                },
            )

        assert response.status_code == 200
        # Worker URL takes priority
        instance.mark_ready.assert_awaited_once_with(
            preview.id,
            "https://worker-provided.example.com",
            "tok-old",
        )

    def test_notify_ready_no_url_falls_back_to_empty(self, client):
        """If no URL is available anywhere, falls back to empty string."""
        preview = _make_preview_session(
            sandbox_id="sb-no-url",
            preview_url=None,
            preview_token=None,
        )

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=preview)
            instance.mark_ready = AsyncMock()

            response = client.post(
                "/api/v1/preview/notify",
                json={"sandbox_id": "sb-no-url", "status": "ready"},
            )

        assert response.status_code == 200
        instance.mark_ready.assert_awaited_once_with(preview.id, "", None)


class TestNotifyFailed:
    """Tests for notify with status=failed."""

    def test_notify_failed_stores_error(self, client):
        """Failed status should pass error message to mark_failed."""
        preview = _make_preview_session(sandbox_id="sb-fail")

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=preview)
            instance.mark_failed = AsyncMock()

            response = client.post(
                "/api/v1/preview/notify",
                json={
                    "sandbox_id": "sb-fail",
                    "status": "failed",
                    "error_message": "Dev server crashed",
                },
            )

        assert response.status_code == 200
        instance.mark_failed.assert_awaited_once_with(preview.id, "Dev server crashed")

    def test_notify_failed_default_error_message(self, client):
        """Failed without error_message should use 'Unknown error'."""
        preview = _make_preview_session(sandbox_id="sb-fail-default")

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=preview)
            instance.mark_failed = AsyncMock()

            response = client.post(
                "/api/v1/preview/notify",
                json={"sandbox_id": "sb-fail-default", "status": "failed"},
            )

        assert response.status_code == 200
        instance.mark_failed.assert_awaited_once_with(preview.id, "Unknown error")


# ============================================================================
# Tests: Error cases
# ============================================================================


class TestNotifyErrors:
    """Tests for notify error handling."""

    def test_notify_unknown_sandbox_returns_404(self, client):
        """Notify for non-existent sandbox should return 404."""
        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/preview/notify",
                json={"sandbox_id": "sb-nonexistent", "status": "ready"},
            )

        assert response.status_code == 404
        assert "No preview for sandbox" in response.json()["detail"]

    def test_notify_invalid_status_returns_400(self, client):
        """Invalid status value should return 400."""
        preview = _make_preview_session(sandbox_id="sb-invalid")

        with patch("omoi_os.api.routes.preview.PreviewManager") as MockManager:
            instance = MockManager.return_value
            instance.get_by_sandbox = AsyncMock(return_value=preview)

            response = client.post(
                "/api/v1/preview/notify",
                json={"sandbox_id": "sb-invalid", "status": "bogus"},
            )

        assert response.status_code == 400
        assert "Invalid status" in response.json()["detail"]

    def test_notify_missing_sandbox_id_returns_422(self, client):
        """Missing sandbox_id should return 422 validation error."""
        response = client.post(
            "/api/v1/preview/notify",
            json={"status": "ready"},
        )
        assert response.status_code == 422
