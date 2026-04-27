"""Tests for session API alias routes.

These tests verify that the /api/v1/sessions endpoints correctly alias
to the /api/v1/tasks handlers with proper deprecation headers and
response transformations.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException, status

from omoi_os.api.routes import sessions


class TestCheckFeatureFlag:
    """Test the feature flag guard function."""

    def test_raises_404_when_feature_disabled(self):
        """Should raise 404 when sessions_api_v1 feature is disabled."""
        with patch(
            "omoi_os.api.routes.sessions.is_feature_enabled", return_value=False
        ):
            with pytest.raises(HTTPException) as exc_info:
                sessions.check_feature_flag()

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not available" in exc_info.value.detail

    def test_passes_when_feature_enabled(self):
        """Should not raise when sessions_api_v1 feature is enabled."""
        with patch("omoi_os.api.routes.sessions.is_feature_enabled", return_value=True):
            # Should not raise
            sessions.check_feature_flag()


class TestAddSessionIdToResponse:
    """Test the response transformation helper."""

    def test_adds_session_id_to_dict_with_id(self):
        """Should add session_id field when id is present."""
        data = {"id": "task-123", "name": "Test Task"}
        result = sessions._add_session_id_to_response(data)

        assert result["id"] == "task-123"
        assert result["session_id"] == "task-123"
        assert result["name"] == "Test Task"

    def test_preserves_existing_session_id(self):
        """Should not overwrite existing session_id."""
        data = {"id": "task-123", "session_id": "existing-456"}
        result = sessions._add_session_id_to_response(data)

        assert result["session_id"] == "existing-456"

    def test_handles_dict_without_id(self):
        """Should not add session_id when id is not present."""
        data = {"name": "Test Task"}
        result = sessions._add_session_id_to_response(data)

        assert "session_id" not in result
        assert result["name"] == "Test Task"

    def test_transforms_list_of_dicts(self):
        """Should transform each item in a list."""
        data = [
            {"id": "task-1", "name": "Task 1"},
            {"id": "task-2", "name": "Task 2"},
        ]
        result = sessions._add_session_id_to_response(data)

        assert len(result) == 2
        assert result[0]["session_id"] == "task-1"
        assert result[1]["session_id"] == "task-2"

    def test_passes_through_non_dict_values(self):
        """Should return non-dict values unchanged."""
        assert sessions._add_session_id_to_response("string") == "string"
        assert sessions._add_session_id_to_response(123) == 123
        assert sessions._add_session_id_to_response(None) is None


class TestTransformRequestBody:
    """Test the request body transformation helper."""

    def test_converts_session_id_to_task_id(self):
        """Should convert session_id to task_id."""
        body = {"session_id": "sess-123", "name": "Test"}
        result = sessions._transform_request_body(body)

        assert result["task_id"] == "sess-123"
        assert "session_id" not in result

    def test_preserves_existing_task_id(self):
        """Should not overwrite existing task_id."""
        body = {"session_id": "sess-123", "task_id": "task-456"}
        result = sessions._transform_request_body(body)

        assert result["task_id"] == "task-456"

    def test_converts_session_type_to_task_type(self):
        """Should convert session_type to task_type."""
        body = {"session_type": "implementation", "name": "Test"}
        result = sessions._transform_request_body(body)

        assert result["task_type"] == "implementation"
        assert "session_type" not in result

    def test_preserves_other_fields(self):
        """Should preserve other fields unchanged."""
        body = {"name": "Test", "priority": "HIGH"}
        result = sessions._transform_request_body(body)

        assert result["name"] == "Test"
        assert result["priority"] == "HIGH"


class TestSetDeprecationHeader:
    """Test the deprecation header setter."""

    def test_sets_x_deprecated_header(self):
        """Should set X-Deprecated header on response."""
        response = MagicMock()
        response.headers = {}

        sessions._set_deprecation_header(response)

        assert response.headers["X-Deprecated"] == sessions.DEPRECATION_HEADER
        assert "Use /api/v1/tasks" in response.headers["X-Deprecated"]


class TestSessionCreateModel:
    """Test the SessionCreate request model."""

    def test_accepts_session_type_alias(self):
        """Should accept session_type as alias for task_type."""
        from omoi_os.api.routes.sessions import SessionCreate

        data = SessionCreate(
            ticket_id="ticket-123",
            title="Test Session",
            description="Test description",
            session_type="exploration",
        )

        assert data.session_type == "exploration"
        assert data.ticket_id == "ticket-123"

    def test_default_values(self):
        """Should have correct default values."""
        from omoi_os.api.routes.sessions import SessionCreate

        data = SessionCreate(
            ticket_id="ticket-123",
            title="Test",
            description="Test desc",
        )

        assert data.session_type == "implementation"
        assert data.priority == "MEDIUM"
        assert data.phase_id == "PHASE_IMPLEMENTATION"


class TestDeprecationHeaderConstant:
    """Test the deprecation header constant."""

    def test_contains_correct_message(self):
        """Should contain the correct deprecation message."""
        assert "Use /api/v1/tasks instead" in sessions.DEPRECATION_HEADER
        assert "Removed in v2.0" in sessions.DEPRECATION_HEADER
