"""Unit tests for PreviewManager service.

Tests preview session lifecycle management with mocked DB and EventBus.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from omoi_os.models.preview_session import PreviewSession, PreviewStatus
from omoi_os.services.preview_manager import PreviewManager
from omoi_os.services.event_bus import SystemEvent

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_db():
    """Create a mock DatabaseService with async session support."""
    db = MagicMock()

    # Create a mock async session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    mock_session.execute = AsyncMock()

    # Make get_async_session return an async context manager
    async_ctx = AsyncMock()
    async_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    async_ctx.__aexit__ = AsyncMock(return_value=False)
    db.get_async_session = MagicMock(return_value=async_ctx)

    # Store session for assertion access
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
    """Create a PreviewManager with mocked dependencies."""
    return PreviewManager(db=mock_db, event_bus=mock_event_bus)


def _make_preview(
    sandbox_id="sb-test-123",
    status=PreviewStatus.PENDING.value,
    preview_url=None,
    preview_token=None,
    task_id=None,
    port=3000,
    framework="vite",
) -> PreviewSession:
    """Create a mock PreviewSession for testing."""
    preview = MagicMock(spec=PreviewSession)
    preview.id = str(uuid4())
    preview.sandbox_id = sandbox_id
    preview.status = status
    preview.preview_url = preview_url
    preview.preview_token = preview_token
    preview.task_id = task_id
    preview.port = port
    preview.framework = framework
    preview.error_message = None
    return preview


# ============================================================================
# Tests: create_preview
# ============================================================================


class TestCreatePreview:
    """Tests for PreviewManager.create_preview."""

    @pytest.mark.asyncio
    async def test_create_preview_success(self, manager, mock_db):
        """Test creating a preview session in PENDING status."""
        # Mock: no existing preview for this sandbox
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db._mock_session.execute.return_value = mock_result

        await manager.create_preview(
            sandbox_id="sb-test-123",
            task_id="task-456",
            port=3000,
            framework="vite",
        )

        # Verify session.add was called
        mock_db._mock_session.add.assert_called_once()
        mock_db._mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_preview_duplicate_raises(self, manager, mock_db):
        """Test that creating a duplicate preview raises ValueError."""
        existing = _make_preview(sandbox_id="sb-dup")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_db._mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Preview already exists"):
            await manager.create_preview(sandbox_id="sb-dup")


# ============================================================================
# Tests: mark_ready
# ============================================================================


class TestMarkReady:
    """Tests for PreviewManager.mark_ready."""

    @pytest.mark.asyncio
    async def test_mark_ready_updates_fields(self, manager, mock_db, mock_event_bus):
        """Test transitioning to READY updates URL, token, and timestamp."""
        preview = _make_preview()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = preview
        mock_db._mock_session.execute.return_value = mock_result

        await manager.mark_ready(
            preview_id=preview.id,
            preview_url="https://sandbox.daytona.io/preview",
            preview_token="tok-abc",
        )

        assert preview.status == PreviewStatus.READY.value
        assert preview.preview_url == "https://sandbox.daytona.io/preview"
        assert preview.preview_token == "tok-abc"
        assert preview.ready_at is not None

    @pytest.mark.asyncio
    async def test_mark_ready_publishes_event(self, manager, mock_db, mock_event_bus):
        """Test that marking ready publishes PREVIEW_READY event."""
        preview = _make_preview(
            sandbox_id="sb-ready", task_id="task-789", framework="vite"
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = preview
        mock_db._mock_session.execute.return_value = mock_result

        await manager.mark_ready(
            preview_id=preview.id,
            preview_url="https://preview.example.com",
        )

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert isinstance(event, SystemEvent)
        assert event.event_type == "PREVIEW_READY"
        assert event.entity_type == "preview_session"
        assert event.payload["preview_url"] == "https://preview.example.com"
        assert event.payload["sandbox_id"] == "sb-ready"

    @pytest.mark.asyncio
    async def test_mark_ready_not_found(self, manager, mock_db):
        """Test marking a non-existent preview raises ValueError."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db._mock_session.execute.return_value = mock_result

        with pytest.raises(ValueError, match="Preview not found"):
            await manager.mark_ready("nonexistent", "https://example.com")


# ============================================================================
# Tests: mark_failed
# ============================================================================


class TestMarkFailed:
    """Tests for PreviewManager.mark_failed."""

    @pytest.mark.asyncio
    async def test_mark_failed_stores_error(self, manager, mock_db):
        """Test transitioning to FAILED stores error message."""
        preview = _make_preview()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = preview
        mock_db._mock_session.execute.return_value = mock_result

        await manager.mark_failed(preview.id, "Dev server crashed on port 3000")

        assert preview.status == PreviewStatus.FAILED.value
        assert preview.error_message == "Dev server crashed on port 3000"


# ============================================================================
# Tests: mark_stopped
# ============================================================================


class TestMarkStopped:
    """Tests for PreviewManager.mark_stopped."""

    @pytest.mark.asyncio
    async def test_mark_stopped_sets_timestamp(self, manager, mock_db):
        """Test transitioning to STOPPED sets stopped_at."""
        preview = _make_preview(status=PreviewStatus.READY.value)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = preview
        mock_db._mock_session.execute.return_value = mock_result

        await manager.mark_stopped(preview.id)

        assert preview.status == PreviewStatus.STOPPED.value
        assert preview.stopped_at is not None


# ============================================================================
# Tests: get_by_sandbox
# ============================================================================


class TestGetBySandbox:
    """Tests for PreviewManager.get_by_sandbox."""

    @pytest.mark.asyncio
    async def test_get_by_sandbox_found(self, manager, mock_db):
        """Test retrieving preview by sandbox ID."""
        preview = _make_preview(sandbox_id="sb-lookup")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = preview
        mock_db._mock_session.execute.return_value = mock_result

        result = await manager.get_by_sandbox("sb-lookup")
        assert result is not None
        assert result.sandbox_id == "sb-lookup"

    @pytest.mark.asyncio
    async def test_get_by_sandbox_not_found(self, manager, mock_db):
        """Test retrieving non-existent sandbox returns None."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db._mock_session.execute.return_value = mock_result

        result = await manager.get_by_sandbox("sb-nonexistent")
        assert result is None
