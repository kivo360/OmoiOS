"""Unit tests for PrototypeManager service.

Tests prototype session lifecycle with mocked Daytona SDK and services.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omoi_os.services.prototype_manager import (
    PrototypeManager,
    PrototypeSession,
    PrototypeStatus,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create a mock DatabaseService with async session support."""
    db = MagicMock()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()

    async_ctx = AsyncMock()
    async_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    async_ctx.__aexit__ = AsyncMock(return_value=False)
    db.get_async_session = MagicMock(return_value=async_ctx)
    db._mock_session = mock_session
    return db


@pytest.fixture
def mock_event_bus():
    """Create a mock EventBusService."""
    event_bus = MagicMock()
    event_bus.publish = MagicMock()
    return event_bus


@pytest.fixture
def manager(mock_db, mock_event_bus):
    """Create a PrototypeManager with mocked dependencies."""
    return PrototypeManager(db=mock_db, event_bus=mock_event_bus)


# ============================================================================
# Tests: start_session
# ============================================================================


class TestStartSession:
    """Tests for PrototypeManager.start_session."""

    @pytest.mark.asyncio
    async def test_start_session_invalid_framework(self, manager):
        """Test that an invalid framework raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported framework"):
            await manager.start_session(user_id="u-1", framework="angular")

    @pytest.mark.asyncio
    async def test_start_session_success(self, manager, mock_db, mock_event_bus):
        """Test successful session start creates sandbox and preview."""
        # Mock Daytona SDK
        mock_sandbox = MagicMock()
        mock_sandbox.id = "sb-proto-123"
        mock_sandbox.process.exec = MagicMock()
        mock_preview_link = MagicMock()
        mock_preview_link.url = "https://preview.example.com"
        mock_preview_link.token = "tok-abc"
        mock_sandbox.get_preview_link = MagicMock(return_value=mock_preview_link)

        mock_daytona = MagicMock()
        mock_daytona.create = MagicMock(return_value=mock_sandbox)

        # Mock the PreviewManager methods on the manager instance
        mock_preview = MagicMock()
        mock_preview.id = "prev-123"
        manager.preview_manager.create_preview = AsyncMock(return_value=mock_preview)
        manager.preview_manager.mark_ready = AsyncMock()

        with (
            patch("daytona.Daytona", return_value=mock_daytona),
            patch("daytona.DaytonaConfig"),
            patch("omoi_os.config.get_app_settings") as mock_settings,
        ):
            mock_settings.return_value.daytona.api_key = "test-key"  # pragma: allowlist secret
            mock_settings.return_value.daytona.api_url = "https://api.daytona.io"
            mock_settings.return_value.daytona.target = "us"

            session = await manager.start_session(
                user_id="u-1", framework="react-vite"
            )

        assert session.status == PrototypeStatus.READY
        assert session.sandbox_id == "sb-proto-123"
        assert session.preview_url == "https://preview.example.com"
        assert session.framework == "react-vite"
        assert session.preview_id == "prev-123"
        mock_event_bus.publish.assert_called()
        manager.preview_manager.mark_ready.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_session_failure_marks_failed(self, manager):
        """Test that a Daytona failure marks session as FAILED."""
        with (
            patch(
                "daytona.Daytona",
                side_effect=RuntimeError("SDK unavailable"),
            ),
            patch("daytona.DaytonaConfig"),
            patch("omoi_os.config.get_app_settings"),
        ):
            session = await manager.start_session(
                user_id="u-1", framework="react-vite"
            )

        assert session.status == PrototypeStatus.FAILED
        assert "SDK unavailable" in session.error_message


# ============================================================================
# Tests: apply_prompt
# ============================================================================


class TestApplyPrompt:
    """Tests for PrototypeManager.apply_prompt."""

    @pytest.mark.asyncio
    async def test_apply_prompt_session_not_found(self, manager):
        """Test prompt on non-existent session raises ValueError."""
        with pytest.raises(ValueError, match="Session not found"):
            await manager.apply_prompt("nonexistent", "hello")

    @pytest.mark.asyncio
    async def test_apply_prompt_success(self, manager, mock_event_bus):
        """Test successful prompt application."""
        # Create a session manually
        session = PrototypeSession(
            id="sess-1",
            user_id="u-1",
            framework="react-vite",
            status=PrototypeStatus.READY,
        )
        manager._sessions["sess-1"] = session

        with patch(
            "omoi_os.services.llm_service.get_llm_service"
        ) as mock_llm_fn:
            mock_llm = MagicMock()
            mock_llm.complete = AsyncMock(
                return_value="Added a counter component to App.tsx"
            )
            mock_llm_fn.return_value = mock_llm

            result = await manager.apply_prompt("sess-1", "Add a counter")

        assert result["prompt"] == "Add a counter"
        assert "counter" in result["response_summary"].lower()
        assert len(session.prompt_history) == 1
        assert session.status == PrototypeStatus.READY
        mock_event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_apply_prompt_wrong_state(self, manager):
        """Test prompt on session in wrong state raises ValueError."""
        session = PrototypeSession(
            id="sess-2",
            user_id="u-1",
            framework="react-vite",
            status=PrototypeStatus.CREATING,
        )
        manager._sessions["sess-2"] = session

        with pytest.raises(ValueError, match="not in a promptable state"):
            await manager.apply_prompt("sess-2", "hello")


# ============================================================================
# Tests: export_to_repo
# ============================================================================


class TestExportToRepo:
    """Tests for PrototypeManager.export_to_repo."""

    @pytest.mark.asyncio
    async def test_export_session_not_found(self, manager):
        """Test export on non-existent session raises ValueError."""
        with pytest.raises(ValueError, match="Session not found"):
            await manager.export_to_repo(
                "nonexistent", repo_url="https://github.com/test/repo"
            )

    @pytest.mark.asyncio
    async def test_export_success(self, manager, mock_event_bus):
        """Test successful export to repo."""
        mock_sandbox = MagicMock()
        mock_sandbox.process.exec = MagicMock()

        session = PrototypeSession(
            id="sess-3",
            user_id="u-1",
            framework="react-vite",
            sandbox_id="sb-export",
            status=PrototypeStatus.READY,
        )
        manager._sessions["sess-3"] = session

        mock_daytona = MagicMock()
        mock_daytona.get_current_sandbox = MagicMock(return_value=mock_sandbox)

        with (
            patch("daytona.Daytona", return_value=mock_daytona),
            patch("daytona.DaytonaConfig"),
            patch("omoi_os.config.get_app_settings") as mock_settings,
        ):
            mock_settings.return_value.daytona.api_key = "test-key"  # pragma: allowlist secret
            mock_settings.return_value.daytona.api_url = "https://api.daytona.io"
            mock_settings.return_value.daytona.target = "us"

            result = await manager.export_to_repo(
                "sess-3",
                repo_url="https://github.com/test/repo",
                branch="prototype",
                commit_message="Export prototype",
            )

        assert result["repo_url"] == "https://github.com/test/repo"
        assert result["branch"] == "prototype"
        assert session.status == PrototypeStatus.READY
        mock_event_bus.publish.assert_called()


# ============================================================================
# Tests: end_session
# ============================================================================


class TestEndSession:
    """Tests for PrototypeManager.end_session."""

    @pytest.mark.asyncio
    async def test_end_session_not_found(self, manager):
        """Test ending non-existent session raises ValueError."""
        with pytest.raises(ValueError, match="Session not found"):
            await manager.end_session("nonexistent")

    @pytest.mark.asyncio
    async def test_end_session_cleanup(self, manager, mock_db):
        """Test ending a session cleans up resources."""
        # Mock no existing preview in DB
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db._mock_session.execute.return_value = mock_result

        session = PrototypeSession(
            id="sess-4",
            user_id="u-1",
            framework="react-vite",
            sandbox_id="sb-cleanup",
            preview_id="prev-cleanup",
            status=PrototypeStatus.READY,
        )
        manager._sessions["sess-4"] = session

        mock_sandbox = MagicMock()
        mock_sandbox.delete = MagicMock()

        mock_daytona = MagicMock()
        mock_daytona.get_current_sandbox = MagicMock(return_value=mock_sandbox)

        with (
            patch("daytona.Daytona", return_value=mock_daytona),
            patch("daytona.DaytonaConfig"),
            patch("omoi_os.config.get_app_settings") as mock_settings,
        ):
            mock_settings.return_value.daytona.api_key = "test-key"  # pragma: allowlist secret
            mock_settings.return_value.daytona.api_url = "https://api.daytona.io"
            mock_settings.return_value.daytona.target = "us"

            await manager.end_session("sess-4")

        # Session should be removed from memory
        assert "sess-4" not in manager._sessions
        mock_sandbox.delete.assert_called_once()


# ============================================================================
# Tests: get_session
# ============================================================================


class TestGetSession:
    """Tests for PrototypeManager.get_session."""

    def test_get_session_found(self, manager):
        """Test retrieving an existing session."""
        session = PrototypeSession(
            id="sess-5", user_id="u-1", framework="react-vite"
        )
        manager._sessions["sess-5"] = session

        result = manager.get_session("sess-5")
        assert result is not None
        assert result.id == "sess-5"

    def test_get_session_not_found(self, manager):
        """Test retrieving non-existent session returns None."""
        result = manager.get_session("nonexistent")
        assert result is None
