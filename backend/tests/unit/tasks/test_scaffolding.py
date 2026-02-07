"""Unit tests for scaffolding tasks."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omoi_os.tasks.scaffolding import (
    trigger_scaffolding,
    trigger_scaffolding_for_ticket,
    _create_spec_from_description,
    _generate_title_from_description,
    _run_spec_state_machine,
)


class TestGenerateTitleFromDescription:
    """Tests for _generate_title_from_description helper."""

    def test_short_description_returns_first_sentence(self):
        """Test that short descriptions return the first sentence."""
        description = "Add user authentication with OAuth2. Support Google and GitHub."
        title = _generate_title_from_description(description)
        assert title == "Add user authentication with OAuth2"

    def test_long_description_truncates_at_word_boundary(self):
        """Test that long descriptions are truncated at word boundary."""
        description = "This is a very long description that goes on and on and on and needs to be truncated at some point because it exceeds the maximum allowed length for a title"
        title = _generate_title_from_description(description)
        assert len(title) <= 100
        assert title.endswith("...")

    def test_medium_description_returns_full_sentence(self):
        """Test that medium-length descriptions return the full first sentence."""
        description = "Implement dark mode toggle for the application"
        title = _generate_title_from_description(description)
        assert title == "Implement dark mode toggle for the application"

    def test_empty_description_returns_empty_string(self):
        """Test that empty descriptions return empty string."""
        description = ""
        title = _generate_title_from_description(description)
        # Empty description splits to [''], first element is ''
        assert title == ""

    def test_single_word_description(self):
        """Test single word descriptions."""
        description = "Authentication"
        title = _generate_title_from_description(description)
        assert title == "Authentication"


class TestCreateSpecFromDescription:
    """Tests for _create_spec_from_description."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database service."""
        db = MagicMock()
        db.get_async_session = MagicMock()
        return db

    @pytest.fixture
    def mock_project(self):
        """Create a mock project."""
        project = MagicMock()
        project.id = "project-123"
        project.github_owner = "test-owner"
        project.github_repo = "test-repo"
        return project

    @pytest.mark.asyncio
    async def test_creates_spec_successfully(self, mock_db, mock_project):
        """Test successful spec creation."""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock project query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        # Mock spec creation - the spec gets its ID from refresh
        mock_spec = MagicMock()
        mock_spec.id = "spec-123"
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        # Make refresh set the id attribute
        async def set_spec_id(spec):
            spec.id = "spec-123"

        mock_session.refresh = AsyncMock(side_effect=set_spec_id)

        mock_db.get_async_session.return_value = mock_session

        with patch("omoi_os.models.spec.Spec") as MockSpec:
            MockSpec.return_value = mock_spec

            spec_id = await _create_spec_from_description(
                db=mock_db,
                project_id="project-123",
                feature_description="Add user authentication",
                user_id="550e8400-e29b-41d4-a716-446655440000",  # Valid UUID
            )

            assert spec_id == "spec-123"
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_project_not_found(self, mock_db):
        """Test returns None when project doesn't exist."""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock project query returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_db.get_async_session.return_value = mock_session

        spec_id = await _create_spec_from_description(
            db=mock_db,
            project_id="nonexistent-project",
            feature_description="Add user authentication",
            user_id="550e8400-e29b-41d4-a716-446655440000",
        )

        assert spec_id is None


class TestRunSpecStateMachine:
    """Tests for _run_spec_state_machine."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database service."""
        db = MagicMock()
        db.get_async_session = MagicMock()
        return db

    @pytest.mark.asyncio
    async def test_runs_state_machine_successfully(self, mock_db):
        """Test successful state machine execution."""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock project query
        mock_project = MagicMock()
        mock_project.github_owner = "test-owner"
        mock_project.github_repo = "test-repo"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_session.execute.return_value = mock_result

        mock_db.get_async_session.return_value = mock_session

        with patch(
            "omoi_os.workers.spec_state_machine.SpecStateMachine"
        ) as MockMachine:
            mock_machine = MagicMock()
            mock_machine.run = AsyncMock(return_value=True)
            MockMachine.return_value = mock_machine

            success = await _run_spec_state_machine(
                db=mock_db,
                spec_id="spec-123",
                project_id="project-123",
            )

            assert success is True
            MockMachine.assert_called_once()
            mock_machine.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, mock_db):
        """Test returns False when state machine raises exception."""
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        # Mock project query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        mock_db.get_async_session.return_value = mock_session

        with patch(
            "omoi_os.workers.spec_state_machine.SpecStateMachine"
        ) as MockMachine:
            MockMachine.side_effect = Exception("State machine error")

            success = await _run_spec_state_machine(
                db=mock_db,
                spec_id="spec-123",
                project_id="project-123",
            )

            assert success is False


class TestTriggerScaffolding:
    """Tests for trigger_scaffolding main function."""

    @pytest.mark.asyncio
    async def test_full_workflow_success(self):
        """Test successful full scaffolding workflow."""
        with patch(
            "omoi_os.api.dependencies.get_database_service"
        ) as mock_get_db, patch(
            "omoi_os.services.event_bus.get_event_bus"
        ) as mock_get_bus, patch(
            "omoi_os.tasks.scaffolding._create_spec_from_description"
        ) as mock_create, patch(
            "omoi_os.tasks.scaffolding._run_spec_state_machine"
        ) as mock_run:

            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_bus = MagicMock()
            mock_get_bus.return_value = mock_bus

            mock_create.return_value = "spec-123"
            mock_run.return_value = True

            result = await trigger_scaffolding(
                project_id="project-123",
                feature_description="Add user authentication",
                user_id="user-123",
            )

            assert result["success"] is True
            assert result["project_id"] == "project-123"
            assert result["spec_id"] == "spec-123"

            # Verify events were published
            assert mock_bus.publish.call_count == 2  # STARTED and COMPLETED

    @pytest.mark.asyncio
    async def test_returns_error_when_spec_creation_fails(self):
        """Test returns error when spec creation fails."""
        with patch(
            "omoi_os.api.dependencies.get_database_service"
        ) as mock_get_db, patch(
            "omoi_os.services.event_bus.get_event_bus"
        ) as mock_get_bus, patch(
            "omoi_os.tasks.scaffolding._create_spec_from_description"
        ) as mock_create:

            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_bus = MagicMock()
            mock_get_bus.return_value = mock_bus

            mock_create.return_value = None  # Spec creation failed

            result = await trigger_scaffolding(
                project_id="project-123",
                feature_description="Add user authentication",
                user_id="user-123",
            )

            assert result["success"] is False
            assert "Failed to create spec" in result["error"]

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        """Test handles exceptions gracefully."""
        with patch(
            "omoi_os.api.dependencies.get_database_service"
        ) as mock_get_db, patch(
            "omoi_os.services.event_bus.get_event_bus"
        ) as mock_get_bus:

            mock_get_db.side_effect = Exception("Database connection failed")

            mock_bus = MagicMock()
            mock_get_bus.return_value = mock_bus

            result = await trigger_scaffolding(
                project_id="project-123",
                feature_description="Add user authentication",
                user_id="user-123",
            )

            assert result["success"] is False
            assert "Database connection failed" in result["error"]


class TestTriggerScaffoldingForTicket:
    """Tests for trigger_scaffolding_for_ticket."""

    @pytest.mark.asyncio
    async def test_uses_ticket_description(self):
        """Test that ticket description is used for scaffolding."""
        with patch(
            "omoi_os.api.dependencies.get_database_service"
        ) as mock_get_db, patch(
            "omoi_os.tasks.scaffolding.trigger_scaffolding"
        ) as mock_trigger:

            # Setup mock database
            mock_db = MagicMock()
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None

            # Mock ticket query
            mock_ticket = MagicMock()
            mock_ticket.title = "Add authentication"
            mock_ticket.description = "We need OAuth2 support"
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_ticket
            mock_session.execute.return_value = mock_result

            mock_db.get_async_session.return_value = mock_session
            mock_get_db.return_value = mock_db

            mock_trigger.return_value = {"success": True, "spec_id": "spec-123"}

            result = await trigger_scaffolding_for_ticket(
                ticket_id="ticket-123",
                project_id="project-123",
                user_id="user-123",
            )

            assert result["success"] is True
            assert result["source_ticket_id"] == "ticket-123"

            # Verify trigger_scaffolding was called with ticket content
            mock_trigger.assert_called_once()
            call_args = mock_trigger.call_args
            assert "Add authentication" in call_args.kwargs["feature_description"]
            assert "OAuth2 support" in call_args.kwargs["feature_description"]

    @pytest.mark.asyncio
    async def test_returns_error_when_ticket_not_found(self):
        """Test returns error when ticket doesn't exist."""
        with patch("omoi_os.api.dependencies.get_database_service") as mock_get_db:

            mock_db = MagicMock()
            mock_session = AsyncMock()
            mock_session.__aenter__.return_value = mock_session
            mock_session.__aexit__.return_value = None

            # Mock ticket query returns None
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_session.execute.return_value = mock_result

            mock_db.get_async_session.return_value = mock_session
            mock_get_db.return_value = mock_db

            result = await trigger_scaffolding_for_ticket(
                ticket_id="nonexistent-ticket",
                project_id="project-123",
                user_id="user-123",
            )

            assert result["success"] is False
            assert "Ticket not found" in result["error"]
