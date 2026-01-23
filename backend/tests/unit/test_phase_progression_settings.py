"""Tests for PhaseProgressionService settings integration."""

import pytest
from unittest.mock import MagicMock, patch

from omoi_os.services.phase_progression_service import PhaseProgressionService
from omoi_os.services.spec_driven_settings import SpecDrivenSettings


class TestPhaseProgressionSettingsIntegration:
    """Tests for PhaseProgressionService respecting spec-driven settings."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database service."""
        return MagicMock()

    @pytest.fixture
    def mock_task_queue(self):
        """Create a mock task queue service."""
        return MagicMock()

    @pytest.fixture
    def mock_phase_gate(self):
        """Create a mock phase gate service."""
        return MagicMock()

    @pytest.fixture
    def mock_settings_service(self):
        """Create a mock settings service."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db, mock_task_queue, mock_phase_gate, mock_settings_service):
        """Create a PhaseProgressionService with mocked dependencies."""
        return PhaseProgressionService(
            db=mock_db,
            task_queue=mock_task_queue,
            phase_gate=mock_phase_gate,
            settings_service=mock_settings_service,
        )

    def test_settings_service_injection(
        self, mock_db, mock_task_queue, mock_phase_gate, mock_settings_service
    ):
        """Test that settings service is properly injected."""
        service = PhaseProgressionService(
            db=mock_db,
            task_queue=mock_task_queue,
            phase_gate=mock_phase_gate,
            settings_service=mock_settings_service,
        )

        assert service.settings_service is mock_settings_service

    def test_handle_task_completed_skips_when_auto_progression_disabled(
        self, service, mock_db, mock_settings_service
    ):
        """Test that auto-advancement is skipped when auto_phase_progression=False."""
        # Setup: ticket exists with project_id
        mock_ticket = MagicMock()
        mock_ticket.project_id = "project-123"

        mock_session = MagicMock()
        mock_session.get.return_value = mock_ticket
        mock_session.query.return_value.filter.return_value.all.return_value = [
            MagicMock(status="completed")  # All tasks completed
        ]
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Settings have auto_phase_progression=False
        mock_settings_service.get_settings.return_value = SpecDrivenSettings(
            auto_phase_progression=False
        )

        # Mock the workflow orchestrator
        mock_orchestrator = MagicMock()
        service.set_workflow_orchestrator(mock_orchestrator)

        # Event data for task completion
        event_data = {
            "entity_id": "task-123",
            "payload": {
                "ticket_id": "ticket-456",
                "phase_id": "PHASE_REQUIREMENTS",
                "task_type": "analyze_requirements",
            },
        }

        # Handle the event
        service._handle_task_completed(event_data)

        # Verify: settings were checked for the project
        mock_settings_service.get_settings.assert_called_once_with("project-123")

        # Verify: check_and_progress_ticket was NOT called (skipped due to setting)
        mock_orchestrator.check_and_progress_ticket.assert_not_called()

    def test_handle_task_completed_proceeds_when_auto_progression_enabled(
        self, service, mock_db, mock_settings_service
    ):
        """Test that auto-advancement proceeds when auto_phase_progression=True."""
        # Setup: ticket exists with project_id
        mock_ticket = MagicMock()
        mock_ticket.project_id = "project-123"

        mock_session = MagicMock()
        mock_session.get.return_value = mock_ticket
        mock_session.query.return_value.filter.return_value.all.return_value = [
            MagicMock(status="completed")  # All tasks completed
        ]
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Settings have auto_phase_progression=True (default)
        mock_settings_service.get_settings.return_value = SpecDrivenSettings(
            auto_phase_progression=True
        )

        # Mock the workflow orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.check_and_progress_ticket.return_value = None  # No transition
        service.set_workflow_orchestrator(mock_orchestrator)

        # Event data for task completion
        event_data = {
            "entity_id": "task-123",
            "payload": {
                "ticket_id": "ticket-456",
                "phase_id": "PHASE_REQUIREMENTS",
                "task_type": "analyze_requirements",
            },
        }

        # Handle the event
        service._handle_task_completed(event_data)

        # Verify: settings were checked for the project
        mock_settings_service.get_settings.assert_called_once_with("project-123")

        # Verify: check_and_progress_ticket WAS called (auto-progression enabled)
        mock_orchestrator.check_and_progress_ticket.assert_called_once_with("ticket-456")

    def test_handle_task_completed_default_enables_progression(
        self, service, mock_db, mock_settings_service
    ):
        """Test that default settings (missing settings) enable progression."""
        # Setup: ticket exists with NO project_id
        mock_ticket = MagicMock()
        mock_ticket.project_id = None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_ticket
        mock_session.query.return_value.filter.return_value.all.return_value = [
            MagicMock(status="completed")  # All tasks completed
        ]
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Settings default to auto_phase_progression=True
        mock_settings_service.get_settings.return_value = SpecDrivenSettings()

        # Mock the workflow orchestrator
        mock_orchestrator = MagicMock()
        mock_orchestrator.check_and_progress_ticket.return_value = None
        service.set_workflow_orchestrator(mock_orchestrator)

        # Event data for task completion
        event_data = {
            "entity_id": "task-123",
            "payload": {
                "ticket_id": "ticket-456",
                "phase_id": "PHASE_REQUIREMENTS",
                "task_type": "analyze_requirements",
            },
        }

        # Handle the event
        service._handle_task_completed(event_data)

        # Verify: check_and_progress_ticket WAS called (default enables progression)
        mock_orchestrator.check_and_progress_ticket.assert_called_once_with("ticket-456")

    def test_implement_feature_completion_not_affected_by_settings(
        self, service, mock_db, mock_settings_service
    ):
        """Test that implement_feature completion ignores auto_phase_progression setting."""
        # Setup for _move_ticket_to_done
        mock_ticket = MagicMock()
        mock_ticket.project_id = "project-123"
        mock_ticket.status = "building"
        mock_ticket.is_blocked = False

        mock_session = MagicMock()
        mock_session.get.return_value = mock_ticket
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Settings have auto_phase_progression=False
        mock_settings_service.get_settings.return_value = SpecDrivenSettings(
            auto_phase_progression=False
        )

        # Event data for implement_feature completion
        event_data = {
            "entity_id": "task-123",
            "payload": {
                "ticket_id": "ticket-456",
                "phase_id": "PHASE_IMPLEMENTATION",
                "task_type": "implement_feature",  # Special case
            },
        }

        # Handle the event
        service._handle_task_completed(event_data)

        # Verify: settings were NOT checked (implement_feature has special handling)
        mock_settings_service.get_settings.assert_not_called()

        # Verify: ticket was moved to done (setting didn't block it)
        # The actual assertion depends on the implementation, but we should see
        # _move_ticket_to_done being called via ticket.status update
        # This is a smoke test that the code path doesn't check settings
