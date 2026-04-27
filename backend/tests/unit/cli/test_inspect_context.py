"""Test inspect_context CLI.

Tests cover:
- CLI argument parsing
- Endpoint handler with mocked TaskContextBuilder
- All output formats (markdown, json, base64)
- Error handling for missing tasks
"""

from __future__ import annotations

import argparse
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from omoi_os.cli.inspect_context import (
    create_parser,
    inspect_task,
    main,
    main_async,
)
from omoi_os.services.task_context_builder import FullTaskContext


def make_mock_context():
    """Create a mock FullTaskContext for testing."""
    return FullTaskContext(
        task_id="test-task-123",
        task_type="implement_feature",
        task_description="Implement the login page",
        task_priority="HIGH",
        phase_id="PHASE_IMPLEMENTATION",
        ticket_id="test-ticket-456",
        ticket_title="Login Feature",
        ticket_description="Add a login page with email/password auth",
        ticket_priority="HIGH",
    )


# =============================================================================
# CLI Argument Parsing Tests
# =============================================================================


class TestCreateParser:
    """Test CLI argument parser."""

    def test_parser_creation(self):
        """Test parser is created successfully."""
        parser = create_parser()
        assert isinstance(parser, argparse.ArgumentParser)

    def test_task_id_required(self):
        """Test task_id is a required positional argument."""
        parser = create_parser()
        # Should raise SystemExit when required arg is missing
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_task_id_parsing(self):
        """Test task_id is parsed correctly."""
        parser = create_parser()
        args = parser.parse_args(["task-123"])
        assert args.task_id == "task-123"

    def test_default_format(self):
        """Test default format is markdown."""
        parser = create_parser()
        args = parser.parse_args(["task-123"])
        assert args.format == "markdown"
        assert args.json is False
        assert args.base64 is False

    def test_json_flag(self):
        """Test --json flag sets format correctly."""
        parser = create_parser()
        args = parser.parse_args(["task-123", "--json"])
        assert args.json is True
        assert args.base64 is False

    def test_base64_flag(self):
        """Test --base64 flag sets format correctly."""
        parser = create_parser()
        args = parser.parse_args(["task-123", "--base64"])
        assert args.json is False
        assert args.base64 is True

    def test_format_option(self):
        """Test --format option overrides default."""
        parser = create_parser()
        args = parser.parse_args(["task-123", "--format", "json"])
        assert args.format == "json"

    def test_format_option_with_base64(self):
        """Test --format base64 works correctly."""
        parser = create_parser()
        args = parser.parse_args(["task-123", "--format", "base64"])
        assert args.format == "base64"


# =============================================================================
# CLI Main Function Tests
# =============================================================================


class TestMainAsync:
    """Test async main function."""

    @pytest.mark.asyncio
    async def test_main_with_markdown_format(self, capsys):
        """Test main with default markdown format."""
        mock_context = make_mock_context()

        with patch(
            "omoi_os.cli.inspect_context.inspect_task", new_callable=AsyncMock
        ) as mock_inspect:
            mock_inspect.return_value = mock_context.to_markdown()
            result = await main_async(["task-123"])

        assert result == 0
        mock_inspect.assert_called_once_with("task-123", "markdown")
        captured = capsys.readouterr()
        assert "Task Context" in captured.out

    @pytest.mark.asyncio
    async def test_main_with_json_flag(self):
        """Test main with --json flag."""
        mock_context = make_mock_context()

        with patch(
            "omoi_os.cli.inspect_context.inspect_task", new_callable=AsyncMock
        ) as mock_inspect:
            mock_inspect.return_value = json.dumps(mock_context.to_dict(), indent=2)
            result = await main_async(["task-123", "--json"])

        assert result == 0
        mock_inspect.assert_called_once_with("task-123", "json")

    @pytest.mark.asyncio
    async def test_main_with_base64_flag(self):
        """Test main with --base64 flag."""
        mock_context = make_mock_context()
        task_data = mock_context.to_dict()
        task_data["_markdown_context"] = mock_context.to_markdown()
        encoded = base64.b64encode(json.dumps(task_data).encode()).decode()

        with patch(
            "omoi_os.cli.inspect_context.inspect_task", new_callable=AsyncMock
        ) as mock_inspect:
            mock_inspect.return_value = encoded
            result = await main_async(["task-123", "--base64"])

        assert result == 0
        mock_inspect.assert_called_once_with("task-123", "base64")

    @pytest.mark.asyncio
    async def test_main_task_not_found(self, capsys):
        """Test main handles ValueError (task not found)."""
        with patch(
            "omoi_os.cli.inspect_context.inspect_task", new_callable=AsyncMock
        ) as mock_inspect:
            mock_inspect.side_effect = ValueError("Task not found: task-999")
            result = await main_async(["task-999"])

        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Task not found" in captured.err

    @pytest.mark.asyncio
    async def test_main_connection_error(self, capsys):
        """Test main handles ConnectionError."""
        with patch(
            "omoi_os.cli.inspect_context.inspect_task", new_callable=AsyncMock
        ) as mock_inspect:
            mock_inspect.side_effect = ConnectionError("Database connection failed")
            result = await main_async(["task-123"])

        assert result == 2
        captured = capsys.readouterr()
        assert "Error:" in captured.err

    @pytest.mark.asyncio
    async def test_main_unexpected_error(self, capsys):
        """Test main handles unexpected errors."""
        with patch(
            "omoi_os.cli.inspect_context.inspect_task", new_callable=AsyncMock
        ) as mock_inspect:
            mock_inspect.side_effect = Exception("Something went wrong")
            result = await main_async(["task-123"])

        assert result == 3
        captured = capsys.readouterr()
        assert "Unexpected error:" in captured.err


class TestMain:
    """Test main entry point."""

    def test_main_runs_async(self):
        """Test main runs the async version."""
        with patch(
            "omoi_os.cli.inspect_context.inspect_task", new_callable=AsyncMock
        ) as mock_inspect:
            mock_inspect.return_value = "mock output"
            result = main(["task-123"])
            assert result in [0, 1, 2, 3]  # Depends on execution


# =============================================================================
# Endpoint Tests (using FastAPI TestClient)
# =============================================================================


class TestInspectTaskContextEndpoint:
    """Test the debug endpoint for inspecting task context."""

    @pytest.mark.unit
    def test_inspect_context_markdown_format(
        self, mock_authenticated_client: TestClient
    ):
        """Test endpoint returns markdown format."""
        mock_context = make_mock_context()

        with patch("omoi_os.api.routes.debug.TaskContextBuilder") as MockBuilder:
            mock_builder_instance = MagicMock()
            mock_builder_instance.build_context = AsyncMock(return_value=mock_context)
            MockBuilder.return_value = mock_builder_instance

            response = mock_authenticated_client.get(
                "/api/v1/debug/tasks/task-123/context?format=markdown"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "markdown"
        assert data["task_id"] == "task-123"
        assert "# Task Context" in data["context"]

    @pytest.mark.unit
    def test_inspect_context_json_format(self, mock_authenticated_client: TestClient):
        """Test endpoint returns json format."""
        mock_context = make_mock_context()

        with patch("omoi_os.api.routes.debug.TaskContextBuilder") as MockBuilder:
            mock_builder_instance = MagicMock()
            mock_builder_instance.build_context = AsyncMock(return_value=mock_context)
            MockBuilder.return_value = mock_builder_instance

            response = mock_authenticated_client.get(
                "/api/v1/debug/tasks/task-123/context?format=json"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "json"
        assert data["task_id"] == "task-123"
        assert "task" in data["context"]
        assert data["context"]["task"]["id"] == "test-task-123"

    @pytest.mark.unit
    def test_inspect_context_base64_format(self, mock_authenticated_client: TestClient):
        """Test endpoint returns base64 format."""
        mock_context = make_mock_context()

        with patch("omoi_os.api.routes.debug.TaskContextBuilder") as MockBuilder:
            mock_builder_instance = MagicMock()
            mock_builder_instance.build_context = AsyncMock(return_value=mock_context)
            MockBuilder.return_value = mock_builder_instance

            response = mock_authenticated_client.get(
                "/api/v1/debug/tasks/task-123/context?format=base64"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "base64"
        assert data["task_id"] == "task-123"
        assert "task_data_base64" in data
        assert "decoded_size_bytes" in data

        # Verify base64 can be decoded
        decoded = base64.b64decode(data["task_data_base64"]).decode()
        decoded_data = json.loads(decoded)
        assert "task" in decoded_data
        assert "_markdown_context" in decoded_data

    @pytest.mark.unit
    def test_inspect_context_task_not_found(
        self, mock_authenticated_client: TestClient
    ):
        """Test endpoint returns 404 when task not found."""
        with patch("omoi_os.api.routes.debug.TaskContextBuilder") as MockBuilder:
            mock_builder_instance = MagicMock()
            mock_builder_instance.build_context = AsyncMock(
                side_effect=ValueError("Task not found: task-999")
            )
            MockBuilder.return_value = mock_builder_instance

            response = mock_authenticated_client.get(
                "/api/v1/debug/tasks/task-999/context"
            )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Task not found" in data["detail"]

    @pytest.mark.unit
    def test_inspect_context_invalid_format(
        self, mock_authenticated_client: TestClient
    ):
        """Test endpoint returns 400 for invalid format."""
        mock_context = make_mock_context()

        with patch("omoi_os.api.routes.debug.TaskContextBuilder") as MockBuilder:
            mock_builder_instance = MagicMock()
            mock_builder_instance.build_context = AsyncMock(return_value=mock_context)
            MockBuilder.return_value = mock_builder_instance

            response = mock_authenticated_client.get(
                "/api/v1/debug/tasks/task-123/context?format=invalid"
            )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid format" in data["detail"]

    @pytest.mark.unit
    def test_inspect_context_default_format(
        self, mock_authenticated_client: TestClient
    ):
        """Test endpoint defaults to markdown format."""
        mock_context = make_mock_context()

        with patch("omoi_os.api.routes.debug.TaskContextBuilder") as MockBuilder:
            mock_builder_instance = MagicMock()
            mock_builder_instance.build_context = AsyncMock(return_value=mock_context)
            MockBuilder.return_value = mock_builder_instance

            response = mock_authenticated_client.get(
                "/api/v1/debug/tasks/task-123/context"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["format"] == "markdown"


# =============================================================================
# Integration-style Tests for inspect_task function
# =============================================================================


class TestInspectTaskFunction:
    """Test the inspect_task async function."""

    @pytest.mark.asyncio
    async def test_inspect_task_markdown(self):
        """Test inspect_task with markdown format."""
        mock_context = make_mock_context()

        with patch("omoi_os.cli.inspect_context.get_app_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            mock_settings.return_value.database.url = "postgresql://test"

            with patch("omoi_os.cli.inspect_context.DatabaseService"):
                with patch(
                    "omoi_os.cli.inspect_context.TaskContextBuilder"
                ) as MockBuilder:
                    mock_builder_instance = MagicMock()
                    mock_builder_instance.build_context = AsyncMock(
                        return_value=mock_context
                    )
                    MockBuilder.return_value = mock_builder_instance

                    result = await inspect_task("task-123", "markdown")

        assert "# Task Context" in result

    @pytest.mark.asyncio
    async def test_inspect_task_json(self):
        """Test inspect_task with json format."""
        mock_context = make_mock_context()

        with patch("omoi_os.cli.inspect_context.get_app_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            mock_settings.return_value.database.url = "postgresql://test"

            with patch("omoi_os.cli.inspect_context.DatabaseService"):
                with patch(
                    "omoi_os.cli.inspect_context.TaskContextBuilder"
                ) as MockBuilder:
                    mock_builder_instance = MagicMock()
                    mock_builder_instance.build_context = AsyncMock(
                        return_value=mock_context
                    )
                    MockBuilder.return_value = mock_builder_instance

                    result = await inspect_task("task-123", "json")

        # Should be valid JSON
        data = json.loads(result)
        assert data["task"]["id"] == "test-task-123"

    @pytest.mark.asyncio
    async def test_inspect_task_base64(self):
        """Test inspect_task with base64 format."""
        mock_context = make_mock_context()

        with patch("omoi_os.cli.inspect_context.get_app_settings") as mock_settings:
            mock_settings.return_value = MagicMock()
            mock_settings.return_value.database.url = "postgresql://test"

            with patch("omoi_os.cli.inspect_context.DatabaseService"):
                with patch(
                    "omoi_os.cli.inspect_context.TaskContextBuilder"
                ) as MockBuilder:
                    mock_builder_instance = MagicMock()
                    mock_builder_instance.build_context = AsyncMock(
                        return_value=mock_context
                    )
                    MockBuilder.return_value = mock_builder_instance

                    result = await inspect_task("task-123", "base64")

        # Should be valid base64
        decoded = base64.b64decode(result).decode()
        data = json.loads(decoded)
        assert "task" in data
        assert "_markdown_context" in data
