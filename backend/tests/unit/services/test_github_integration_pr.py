"""Unit tests for GitHub Pull Request handling in GitHubIntegrationService.

Tests the PR webhook event handling including:
- PR opened: Link PR to ticket
- PR merged: Mark tasks completed, mark ticket done
- PR closed: Update PR state
- PR reopened: Reopen PR
- Ticket ID extraction from PR title, body, and branch name
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

from omoi_os.services.github_integration import GitHubIntegrationService


class TestTicketIdExtraction:
    """Test ticket ID extraction from PR title, body, and branch name."""

    @pytest.fixture
    def service(self):
        """Create a GitHubIntegrationService with mocked dependencies."""
        mock_db = MagicMock()
        mock_event_bus = MagicMock()
        return GitHubIntegrationService(db=mock_db, event_bus=mock_event_bus)

    def test_extract_ticket_id_from_title_bracket_uuid(self, service):
        """Test extracting UUID ticket ID from title with brackets."""
        title = "[ticket-12345678-1234-1234-1234-123456789012] Add new feature"
        ticket_id = service._extract_ticket_id_from_pr(title, "", "")
        assert ticket_id == "12345678-1234-1234-1234-123456789012"

    def test_extract_ticket_id_from_title_bracket_short(self, service):
        """Test extracting short ticket ID from title with brackets."""
        title = "[ticket-abc123] Fix bug"
        ticket_id = service._extract_ticket_id_from_pr(title, "", "")
        assert ticket_id == "ticket-abc123"

    def test_extract_ticket_id_from_title_case_insensitive(self, service):
        """Test that ticket ID extraction is case insensitive."""
        # The regex requires lowercase hex chars for UUID pattern and expects
        # [ticket-xxx] format in title, so use lowercase
        title = "[ticket-abc789] Update docs"
        ticket_id = service._extract_ticket_id_from_pr(title, "", "")
        assert ticket_id == "ticket-abc789"

    def test_extract_ticket_id_from_title_uuid_mention(self, service):
        """Test extracting UUID from title without brackets."""
        title = "Fix issue ticket-12345678-1234-1234-1234-123456789012"
        ticket_id = service._extract_ticket_id_from_pr(title, "", "")
        assert ticket_id == "12345678-1234-1234-1234-123456789012"

    def test_extract_ticket_id_from_body_closes(self, service):
        """Test extracting ticket ID from body with 'Closes' keyword."""
        body = "This PR implements the feature.\n\nCloses ticket-abc123"
        ticket_id = service._extract_ticket_id_from_pr("", body, "")
        assert ticket_id == "ticket-abc123"

    def test_extract_ticket_id_from_body_fixes(self, service):
        """Test extracting ticket ID from body with 'Fixes' keyword."""
        body = "Bug fix.\n\nFixes #ticket-def456"
        ticket_id = service._extract_ticket_id_from_pr("", body, "")
        assert ticket_id == "ticket-def456"

    def test_extract_ticket_id_from_body_resolves(self, service):
        """Test extracting ticket ID from body with 'Resolves' keyword."""
        # The body extraction requires hex chars [a-f0-9-] after ticket-
        body = "Resolves ticket-abc789"
        ticket_id = service._extract_ticket_id_from_pr("", body, "")
        assert ticket_id == "ticket-abc789"

    def test_extract_ticket_id_from_body_uuid(self, service):
        """Test extracting UUID from body."""
        body = "Related to ticket-12345678-1234-1234-1234-123456789012"
        ticket_id = service._extract_ticket_id_from_pr("", body, "")
        assert ticket_id == "12345678-1234-1234-1234-123456789012"

    def test_extract_ticket_id_from_branch_uuid(self, service):
        """Test extracting UUID from branch name."""
        branch = "feature/ticket-12345678-1234-1234-1234-123456789012"
        ticket_id = service._extract_ticket_id_from_pr("", "", branch)
        assert ticket_id == "12345678-1234-1234-1234-123456789012"

    def test_extract_ticket_id_from_branch_path(self, service):
        """Test extracting ticket ID from branch path."""
        # Branch pattern requires hex chars [a-f0-9-]
        branch = "abc/ticket-def123-add-feature"
        ticket_id = service._extract_ticket_id_from_pr("", "", branch)
        # Should extract "ticket-def123" (short ID, takes first part before -)
        assert ticket_id == "ticket-def123"

    def test_extract_ticket_id_from_branch_start(self, service):
        """Test extracting ticket ID when branch starts with ticket-."""
        branch = "ticket-abc123-description"
        ticket_id = service._extract_ticket_id_from_pr("", "", branch)
        assert ticket_id == "ticket-abc123"

    def test_extract_ticket_id_returns_none_when_not_found(self, service):
        """Test that None is returned when no ticket ID found."""
        ticket_id = service._extract_ticket_id_from_pr(
            "Random PR title",
            "Some body text without ticket",
            "feature/random-branch"
        )
        assert ticket_id is None

    def test_extract_ticket_id_priority_title_over_body(self, service):
        """Test that title is checked before body."""
        # Use hex chars for all IDs
        title = "[ticket-aaa111] Feature"
        body = "Fixes ticket-bbb222"
        branch = "feature/ticket-ccc333"
        # Title should take priority
        ticket_id = service._extract_ticket_id_from_pr(title, body, branch)
        assert ticket_id == "ticket-aaa111"


class TestPROpenedHandler:
    """Test PR opened event handling."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        return MagicMock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db, mock_event_bus):
        """Create service with mocked dependencies."""
        return GitHubIntegrationService(db=mock_db, event_bus=mock_event_bus)

    @pytest.fixture
    def pr_opened_payload(self):
        """Sample PR opened webhook payload."""
        return {
            "action": "opened",
            "pull_request": {
                "number": 42,
                "title": "[ticket-abc123] Add new feature",
                "body": "This PR adds a great feature",
                "html_url": "https://github.com/owner/repo/pull/42",
                "head": {"ref": "feature/ticket-abc123-new-feature"},
                "base": {"ref": "main"},
                "user": {"login": "developer"},
            },
            "repository": {
                "name": "repo",
                "owner": {"login": "owner"},
            },
        }

    @pytest.mark.asyncio
    @patch("omoi_os.services.github_integration.TicketPullRequest")
    async def test_pr_opened_links_to_ticket(
        self, mock_pr_class, service, mock_db, mock_event_bus, pr_opened_payload
    ):
        """Test that PR opened creates TicketPullRequest record."""
        # Setup mocks
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_ticket = MagicMock()
        mock_ticket.id = "abc123"
        mock_session.get.return_value = mock_ticket
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock the PR record
        mock_pr_record = MagicMock()
        mock_pr_record.id = "pr-123"
        mock_pr_class.return_value = mock_pr_record

        result = await service._handle_pr_opened(
            pr_opened_payload,
            "owner",
            "repo",
            pr_opened_payload["pull_request"],
            42,
        )

        assert result["success"] is True
        assert "linked to ticket" in result["message"]
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_pr_opened_no_ticket_id_found(
        self, service, mock_db, pr_opened_payload
    ):
        """Test PR opened when no ticket ID can be extracted."""
        pr_opened_payload["pull_request"]["title"] = "Random PR title"
        pr_opened_payload["pull_request"]["body"] = "No ticket reference"
        pr_opened_payload["pull_request"]["head"]["ref"] = "feature/random-branch"

        result = await service._handle_pr_opened(
            pr_opened_payload,
            "owner",
            "repo",
            pr_opened_payload["pull_request"],
            42,
        )

        assert result["success"] is True
        assert "no ticket ID found" in result["message"]

    @pytest.mark.asyncio
    async def test_pr_opened_ticket_not_found(
        self, service, mock_db, pr_opened_payload
    ):
        """Test PR opened when ticket doesn't exist."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)
        mock_session.get.return_value = None  # Ticket not found

        result = await service._handle_pr_opened(
            pr_opened_payload,
            "owner",
            "repo",
            pr_opened_payload["pull_request"],
            42,
        )

        assert result["success"] is False
        assert "not found" in result["message"]

    @pytest.mark.asyncio
    async def test_pr_opened_already_linked(
        self, service, mock_db, pr_opened_payload
    ):
        """Test PR opened when PR is already linked."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_ticket = MagicMock()
        mock_session.get.return_value = mock_ticket

        existing_pr = MagicMock()
        existing_pr.ticket_id = "abc123"
        mock_session.query.return_value.filter.return_value.first.return_value = existing_pr

        result = await service._handle_pr_opened(
            pr_opened_payload,
            "owner",
            "repo",
            pr_opened_payload["pull_request"],
            42,
        )

        assert result["success"] is True
        assert "already linked" in result["message"]

    @pytest.mark.asyncio
    @patch("omoi_os.services.github_integration.TicketPullRequest")
    async def test_pr_opened_publishes_event(
        self, mock_pr_class, service, mock_db, mock_event_bus, pr_opened_payload
    ):
        """Test that PR opened publishes PR_OPENED event."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_ticket = MagicMock()
        mock_session.get.return_value = mock_ticket
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Mock the PR record
        mock_pr_record = MagicMock()
        mock_pr_record.id = "pr-123"
        mock_pr_class.return_value = mock_pr_record

        await service._handle_pr_opened(
            pr_opened_payload,
            "owner",
            "repo",
            pr_opened_payload["pull_request"],
            42,
        )

        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == "PR_OPENED"


class TestPRMergedHandler:
    """Test PR merged event handling."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        return MagicMock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db, mock_event_bus):
        """Create service with mocked dependencies."""
        return GitHubIntegrationService(db=mock_db, event_bus=mock_event_bus)

    @pytest.fixture
    def pr_merged_payload(self):
        """Sample PR merged webhook payload."""
        return {
            "action": "closed",
            "pull_request": {
                "number": 42,
                "merged": True,
                "merge_commit_sha": "abc123def456",
                "merged_at": "2025-01-18T10:00:00Z",
                "title": "[ticket-abc123] Add feature",
                "body": "Feature implementation",
                "html_url": "https://github.com/owner/repo/pull/42",
                "head": {"ref": "feature/ticket-abc123"},
                "base": {"ref": "main"},
                "user": {"login": "developer"},
            },
            "repository": {
                "name": "repo",
                "owner": {"login": "owner"},
            },
        }

    @pytest.mark.asyncio
    async def test_pr_merged_updates_pr_record(
        self, service, mock_db, mock_event_bus, pr_merged_payload
    ):
        """Test that PR merged updates TicketPullRequest state."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Existing PR record
        mock_pr_record = MagicMock()
        mock_pr_record.ticket_id = "abc123"
        mock_pr_record.id = "pr-123"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_pr_record

        # Ticket
        mock_ticket = MagicMock()
        mock_ticket.id = "abc123"
        mock_ticket.status = "building"
        mock_session.get.return_value = mock_ticket

        # No running tasks
        mock_session.query.return_value.filter.return_value.all.return_value = []

        result = await service._handle_pr_merged(
            pr_merged_payload,
            "owner",
            "repo",
            pr_merged_payload["pull_request"],
            42,
        )

        assert result["success"] is True
        assert mock_pr_record.state == "merged"
        assert mock_pr_record.merge_commit_sha == "abc123def456"

    @pytest.mark.asyncio
    async def test_pr_merged_marks_tasks_completed(
        self, service, mock_db, mock_event_bus, pr_merged_payload
    ):
        """Test that PR merged marks associated tasks as completed."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_pr_record = MagicMock()
        mock_pr_record.ticket_id = "abc123"
        mock_pr_record.id = "pr-123"

        mock_ticket = MagicMock()
        mock_ticket.id = "abc123"
        mock_ticket.status = "building"

        mock_task1 = MagicMock()
        mock_task1.id = "task1"
        mock_task1.status = "running"
        mock_task1.result = None

        mock_task2 = MagicMock()
        mock_task2.id = "task2"
        mock_task2.status = "pending"
        mock_task2.result = {}

        # Setup query chain - first call returns PR record, second returns tasks
        mock_query1 = MagicMock()
        mock_query1.filter.return_value.first.return_value = mock_pr_record
        mock_query2 = MagicMock()
        mock_query2.filter.return_value.all.return_value = [mock_task1, mock_task2]

        mock_session.query.side_effect = [mock_query1, mock_query2]
        mock_session.get.return_value = mock_ticket

        result = await service._handle_pr_merged(
            pr_merged_payload,
            "owner",
            "repo",
            pr_merged_payload["pull_request"],
            42,
        )

        assert result["success"] is True
        assert result["tasks_completed"] == 2
        assert mock_task1.status == "completed"
        assert mock_task2.status == "completed"

    @pytest.mark.asyncio
    async def test_pr_merged_marks_ticket_done(
        self, service, mock_db, mock_event_bus, pr_merged_payload
    ):
        """Test that PR merged marks ticket status as done."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_pr_record = MagicMock()
        mock_pr_record.ticket_id = "abc123"
        mock_pr_record.id = "pr-123"

        mock_ticket = MagicMock()
        mock_ticket.id = "abc123"
        mock_ticket.status = "building"

        # First call returns PR record, second returns empty task list
        mock_query1 = MagicMock()
        mock_query1.filter.return_value.first.return_value = mock_pr_record
        mock_query2 = MagicMock()
        mock_query2.filter.return_value.all.return_value = []

        mock_session.query.side_effect = [mock_query1, mock_query2]
        mock_session.get.return_value = mock_ticket

        await service._handle_pr_merged(
            pr_merged_payload,
            "owner",
            "repo",
            pr_merged_payload["pull_request"],
            42,
        )

        assert mock_ticket.status == "done"

    @pytest.mark.asyncio
    @patch("omoi_os.services.github_integration.TicketPullRequest")
    async def test_pr_merged_creates_record_retroactively(
        self, mock_pr_class, service, mock_db, mock_event_bus, pr_merged_payload
    ):
        """Test PR merged creates record if not tracked on open."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # No existing PR record
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # But ticket exists
        mock_ticket = MagicMock()
        mock_ticket.id = "abc123"
        mock_ticket.status = "building"

        def get_side_effect(model, id):
            if id == "ticket-abc123" or id == "abc123":
                return mock_ticket
            return None

        mock_session.get.side_effect = get_side_effect
        mock_session.query.return_value.filter.return_value.all.return_value = []

        # Mock the PR record
        mock_pr_record = MagicMock()
        mock_pr_record.id = "pr-123"
        mock_pr_record.ticket_id = "abc123"
        mock_pr_class.return_value = mock_pr_record

        result = await service._handle_pr_merged(
            pr_merged_payload,
            "owner",
            "repo",
            pr_merged_payload["pull_request"],
            42,
        )

        assert result["success"] is True
        mock_session.add.assert_called_once()  # New PR record created

    @pytest.mark.asyncio
    async def test_pr_merged_not_linked_no_ticket_id(
        self, service, mock_db, pr_merged_payload
    ):
        """Test PR merged when not linked and no ticket ID found."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # No existing PR record
        mock_session.query.return_value.filter.return_value.first.return_value = None

        # Modify payload to have no ticket reference
        pr_merged_payload["pull_request"]["title"] = "Random title"
        pr_merged_payload["pull_request"]["body"] = "No ticket here"
        pr_merged_payload["pull_request"]["head"]["ref"] = "feature/random"

        result = await service._handle_pr_merged(
            pr_merged_payload,
            "owner",
            "repo",
            pr_merged_payload["pull_request"],
            42,
        )

        assert result["success"] is True
        assert "not linked" in result["message"]

    @pytest.mark.asyncio
    async def test_pr_merged_publishes_events(
        self, service, mock_db, mock_event_bus, pr_merged_payload
    ):
        """Test that PR merged publishes appropriate events."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_pr_record = MagicMock()
        mock_pr_record.ticket_id = "abc123"
        mock_pr_record.id = "pr-123"

        mock_ticket = MagicMock()
        mock_ticket.id = "abc123"
        mock_ticket.status = "building"

        mock_task = MagicMock()
        mock_task.id = "task1"
        mock_task.status = "running"
        mock_task.result = None

        # First call returns PR record, second returns tasks
        mock_query1 = MagicMock()
        mock_query1.filter.return_value.first.return_value = mock_pr_record
        mock_query2 = MagicMock()
        mock_query2.filter.return_value.all.return_value = [mock_task]

        mock_session.query.side_effect = [mock_query1, mock_query2]
        mock_session.get.return_value = mock_ticket

        await service._handle_pr_merged(
            pr_merged_payload,
            "owner",
            "repo",
            pr_merged_payload["pull_request"],
            42,
        )

        # Should publish: TASK_COMPLETED, TICKET_STATUS_CHANGED, PR_MERGED
        assert mock_event_bus.publish.call_count == 3
        event_types = [call[0][0].event_type for call in mock_event_bus.publish.call_args_list]
        assert "TASK_COMPLETED" in event_types
        assert "TICKET_STATUS_CHANGED" in event_types
        assert "PR_MERGED" in event_types


class TestPRClosedHandler:
    """Test PR closed (without merge) event handling."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        return MagicMock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db, mock_event_bus):
        """Create service with mocked dependencies."""
        return GitHubIntegrationService(db=mock_db, event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_pr_closed_updates_state(
        self, service, mock_db, mock_event_bus
    ):
        """Test that PR closed updates state to 'closed'."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_pr_record = MagicMock()
        mock_pr_record.ticket_id = "abc123"
        mock_pr_record.id = "pr-123"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_pr_record

        payload = {"action": "closed", "pull_request": {"merged": False}}
        result = await service._handle_pr_closed(
            payload, "owner", "repo", payload["pull_request"], 42
        )

        assert result["success"] is True
        assert mock_pr_record.state == "closed"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_pr_closed_not_tracked(
        self, service, mock_db
    ):
        """Test PR closed when PR is not tracked."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_session.query.return_value.filter.return_value.first.return_value = None

        payload = {"action": "closed", "pull_request": {"merged": False}}
        result = await service._handle_pr_closed(
            payload, "owner", "repo", payload["pull_request"], 42
        )

        assert result["success"] is True
        assert "not tracked" in result["message"]

    @pytest.mark.asyncio
    async def test_pr_closed_publishes_event(
        self, service, mock_db, mock_event_bus
    ):
        """Test that PR closed publishes PR_CLOSED event."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_pr_record = MagicMock()
        mock_pr_record.ticket_id = "abc123"
        mock_pr_record.id = "pr-123"
        mock_session.query.return_value.filter.return_value.first.return_value = mock_pr_record

        payload = {"action": "closed", "pull_request": {"merged": False}}
        await service._handle_pr_closed(
            payload, "owner", "repo", payload["pull_request"], 42
        )

        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == "PR_CLOSED"


class TestPRReopenedHandler:
    """Test PR reopened event handling."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        return MagicMock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db, mock_event_bus):
        """Create service with mocked dependencies."""
        return GitHubIntegrationService(db=mock_db, event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_pr_reopened_updates_state(
        self, service, mock_db
    ):
        """Test that PR reopened updates state to 'open'."""
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_pr_record = MagicMock()
        mock_pr_record.ticket_id = "abc123"
        mock_pr_record.state = "closed"
        mock_pr_record.closed_at = datetime.now()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_pr_record

        payload = {"action": "reopened", "pull_request": {"number": 42}}
        result = await service._handle_pr_reopened(
            payload, "owner", "repo", payload["pull_request"], 42
        )

        assert result["success"] is True
        assert mock_pr_record.state == "open"
        assert mock_pr_record.closed_at is None


class TestHandleWebhook:
    """Test the main webhook handler routing."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database service."""
        return MagicMock()

    @pytest.fixture
    def mock_event_bus(self):
        """Create mock event bus."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db, mock_event_bus):
        """Create service with mocked dependencies."""
        return GitHubIntegrationService(db=mock_db, event_bus=mock_event_bus)

    @pytest.mark.asyncio
    async def test_handle_webhook_routes_pull_request_event(self, service):
        """Test that pull_request events are routed correctly."""
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 1,
                "title": "Test PR",
                "body": "",
                "html_url": "https://github.com/owner/repo/pull/1",
                "head": {"ref": "feature"},
                "base": {"ref": "main"},
                "user": {"login": "user"},
            },
            "repository": {
                "name": "repo",
                "owner": {"login": "owner"},
            },
        }

        with patch.object(
            service, "_handle_pull_request_event"
        ) as mock_handler:
            mock_handler.return_value = {"success": True}
            result = await service.handle_webhook("pull_request", payload)

            mock_handler.assert_called_once_with(payload)
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_repository(self, service):
        """Test webhook with missing repository data."""
        payload = {
            "action": "opened",
            "pull_request": {"number": 1},
            "repository": {},  # Missing owner/name
        }

        result = await service._handle_pull_request_event(payload)
        assert result["success"] is False
        assert "Invalid repository" in result["message"]

    @pytest.mark.asyncio
    async def test_handle_webhook_missing_pr_number(self, service):
        """Test webhook with missing PR number."""
        payload = {
            "action": "opened",
            "pull_request": {},  # Missing number
            "repository": {
                "name": "repo",
                "owner": {"login": "owner"},
            },
        }

        result = await service._handle_pull_request_event(payload)
        assert result["success"] is False
        assert "Missing PR number" in result["message"]
