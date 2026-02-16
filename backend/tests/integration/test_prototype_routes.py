"""Integration tests for prototype API routes.

Tests the prototype REST API endpoints with mocked PrototypeManager.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from omoi_os.services.prototype_manager import (
    PrototypeManager,
    PrototypeSession,
    PrototypeStatus,
)

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


def _make_session(
    session_id=None,
    user_id="u-1",
    framework="react-vite",
    status=PrototypeStatus.READY,
    sandbox_id="sb-proto-123",
    preview_id="prev-123",
    preview_url="https://preview.example.com",
) -> PrototypeSession:
    """Create a PrototypeSession for testing."""
    return PrototypeSession(
        id=session_id or str(uuid4()),
        user_id=user_id,
        framework=framework,
        status=status,
        sandbox_id=sandbox_id,
        preview_id=preview_id,
        preview_url=preview_url,
    )


@pytest.fixture
def mock_manager():
    """Create a mock PrototypeManager."""
    manager = MagicMock(spec=PrototypeManager)
    manager.start_session = AsyncMock()
    manager.get_session = MagicMock()
    manager.apply_prompt = AsyncMock()
    manager.export_to_repo = AsyncMock()
    manager.end_session = AsyncMock()
    return manager


@pytest.fixture
def app(mock_user, mock_manager):
    """Create a FastAPI test app with mocked dependencies."""
    from omoi_os.api.routes.prototype import router
    from omoi_os.api.dependencies import get_current_user, get_prototype_manager

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/prototype")

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_prototype_manager] = lambda: mock_manager

    return app


@pytest.fixture
def client(app):
    """Create a TestClient."""
    return TestClient(app)


# ============================================================================
# Tests: POST /api/v1/prototype/session
# ============================================================================


class TestStartSessionRoute:
    """Tests for POST /api/v1/prototype/session."""

    def test_start_session_201(self, client, mock_manager):
        """Test starting a session returns 201."""
        session = _make_session()
        mock_manager.start_session.return_value = session

        response = client.post(
            "/api/v1/prototype/session",
            json={"framework": "react-vite"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["framework"] == "react-vite"
        assert data["status"] == "ready"
        assert data["preview_url"] == "https://preview.example.com"

    def test_start_session_bad_framework_400(self, client, mock_manager):
        """Test starting session with invalid framework returns 400."""
        mock_manager.start_session.side_effect = ValueError(
            "Unsupported framework: angular"
        )

        response = client.post(
            "/api/v1/prototype/session",
            json={"framework": "angular"},
        )

        assert response.status_code == 400
        assert "Unsupported framework" in response.json()["detail"]


# ============================================================================
# Tests: GET /api/v1/prototype/session/{session_id}
# ============================================================================


class TestGetSessionRoute:
    """Tests for GET /api/v1/prototype/session/{session_id}."""

    def test_get_session_200(self, client, mock_manager):
        """Test getting an existing session returns 200."""
        session = _make_session(session_id="sess-get")
        mock_manager.get_session.return_value = session

        response = client.get("/api/v1/prototype/session/sess-get")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "sess-get"
        assert data["framework"] == "react-vite"

    def test_get_session_404(self, client, mock_manager):
        """Test getting non-existent session returns 404."""
        mock_manager.get_session.return_value = None

        response = client.get("/api/v1/prototype/session/nonexistent")

        assert response.status_code == 404


# ============================================================================
# Tests: POST /api/v1/prototype/session/{session_id}/prompt
# ============================================================================


class TestApplyPromptRoute:
    """Tests for POST /api/v1/prototype/session/{id}/prompt."""

    def test_apply_prompt_200(self, client, mock_manager):
        """Test applying a prompt returns 200."""
        mock_manager.apply_prompt.return_value = {
            "prompt": "Add a counter",
            "response_summary": "Added counter component",
            "timestamp": "2026-02-07T12:00:00Z",
        }

        response = client.post(
            "/api/v1/prototype/session/sess-1/prompt",
            json={"prompt": "Add a counter"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["prompt"] == "Add a counter"
        assert data["response_summary"] == "Added counter component"

    def test_apply_prompt_not_found_404(self, client, mock_manager):
        """Test prompt on non-existent session returns 404."""
        mock_manager.apply_prompt.side_effect = ValueError(
            "Session not found: nonexistent"
        )

        response = client.post(
            "/api/v1/prototype/session/nonexistent/prompt",
            json={"prompt": "hello"},
        )

        assert response.status_code == 404


# ============================================================================
# Tests: POST /api/v1/prototype/session/{session_id}/export
# ============================================================================


class TestExportRoute:
    """Tests for POST /api/v1/prototype/session/{id}/export."""

    def test_export_200(self, client, mock_manager):
        """Test exporting to repo returns 200."""
        mock_manager.export_to_repo.return_value = {
            "repo_url": "https://github.com/test/repo",
            "branch": "prototype",
            "commit_message": "Export prototype",
            "timestamp": "2026-02-07T12:00:00Z",
        }

        response = client.post(
            "/api/v1/prototype/session/sess-1/export",
            json={
                "repo_url": "https://github.com/test/repo",
                "branch": "prototype",
                "commit_message": "Export prototype",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["repo_url"] == "https://github.com/test/repo"
        assert data["branch"] == "prototype"


# ============================================================================
# Tests: DELETE /api/v1/prototype/session/{session_id}
# ============================================================================


class TestEndSessionRoute:
    """Tests for DELETE /api/v1/prototype/session/{session_id}."""

    def test_end_session_204(self, client, mock_manager):
        """Test ending a session returns 204 No Content."""
        mock_manager.end_session.return_value = None

        response = client.delete("/api/v1/prototype/session/sess-1")

        assert response.status_code == 204

    def test_end_session_not_found(self, client, mock_manager):
        """Test ending non-existent session returns 404."""
        mock_manager.end_session.side_effect = ValueError(
            "Session not found: nonexistent"
        )

        response = client.delete("/api/v1/prototype/session/nonexistent")

        assert response.status_code == 404
