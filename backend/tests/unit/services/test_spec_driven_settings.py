"""Unit tests for SpecDrivenSettingsService."""

from unittest.mock import MagicMock, patch

import pytest

from omoi_os.services.spec_driven_settings import (
    DEFAULT_SETTINGS,
    GateEnforcementStrictness,
    SpecDrivenSettings,
    SpecDrivenSettingsService,
)


@pytest.mark.unit
class TestSpecDrivenSettings:
    """Tests for the SpecDrivenSettings dataclass."""

    def test_default_settings(self):
        """Default settings should have expected values."""
        settings = SpecDrivenSettings()
        assert settings.gate_enforcement_strictness == GateEnforcementStrictness.STRICT
        assert settings.min_test_coverage == 80
        assert settings.auto_phase_progression is True
        assert settings.guardian_auto_steering is True

    def test_custom_settings(self):
        """Custom settings should override defaults."""
        settings = SpecDrivenSettings(
            gate_enforcement_strictness=GateEnforcementStrictness.LENIENT,
            min_test_coverage=70,
            auto_phase_progression=False,
            guardian_auto_steering=False,
        )
        assert settings.gate_enforcement_strictness == GateEnforcementStrictness.LENIENT
        assert settings.min_test_coverage == 70
        assert settings.auto_phase_progression is False
        assert settings.guardian_auto_steering is False


@pytest.mark.unit
class TestGateEnforcementStrictness:
    """Tests for the GateEnforcementStrictness enum."""

    def test_strictness_values(self):
        """Enum should have expected values."""
        assert GateEnforcementStrictness.BYPASS.value == "bypass"
        assert GateEnforcementStrictness.LENIENT.value == "lenient"
        assert GateEnforcementStrictness.STRICT.value == "strict"

    def test_strictness_from_string(self):
        """Enum should be constructable from string values."""
        assert GateEnforcementStrictness("bypass") == GateEnforcementStrictness.BYPASS
        assert GateEnforcementStrictness("lenient") == GateEnforcementStrictness.LENIENT
        assert GateEnforcementStrictness("strict") == GateEnforcementStrictness.STRICT

    def test_invalid_strictness_value(self):
        """Invalid string should raise ValueError."""
        with pytest.raises(ValueError):
            GateEnforcementStrictness("invalid")


@pytest.mark.unit
class TestSpecDrivenSettingsService:
    """Tests for SpecDrivenSettingsService."""

    def test_get_settings_for_project_no_project_id(self):
        """Should return defaults when project_id is None."""
        mock_db = MagicMock()
        service = SpecDrivenSettingsService(mock_db)

        settings = service.get_settings_for_project(None)

        assert settings == DEFAULT_SETTINGS
        mock_db.get_session.assert_not_called()

    def test_get_settings_for_project_not_found(self):
        """Should return defaults when project is not found."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_project("nonexistent-project")

        assert settings == DEFAULT_SETTINGS
        mock_session.get.assert_called_once()

    def test_get_settings_for_project_no_settings(self):
        """Should return defaults when project has no settings."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.settings = None
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_project("project-123")

        assert settings == DEFAULT_SETTINGS

    def test_get_settings_for_project_with_settings(self):
        """Should parse settings from project."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.settings = {
            "gate_enforcement_strictness": "lenient",
            "min_test_coverage": 70,
            "auto_phase_progression": False,
            "guardian_auto_steering": False,
        }
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_project("project-123")

        assert settings.gate_enforcement_strictness == GateEnforcementStrictness.LENIENT
        assert settings.min_test_coverage == 70
        assert settings.auto_phase_progression is False
        assert settings.guardian_auto_steering is False

    def test_get_settings_for_project_bypass_strictness(self):
        """Should parse bypass strictness correctly."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.settings = {
            "gate_enforcement_strictness": "bypass",
        }
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_project("project-123")

        assert settings.gate_enforcement_strictness == GateEnforcementStrictness.BYPASS

    def test_get_settings_for_project_invalid_strictness(self):
        """Should use default for invalid strictness value."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.settings = {
            "gate_enforcement_strictness": "invalid_value",
        }
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_project("project-123")

        assert settings.gate_enforcement_strictness == GateEnforcementStrictness.STRICT

    def test_get_settings_for_project_invalid_coverage_value(self):
        """Should use default for non-numeric coverage value."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.settings = {
            "min_test_coverage": "not_a_number",
        }
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_project("project-123")

        assert settings.min_test_coverage == 80

    def test_get_settings_for_project_coverage_out_of_range(self):
        """Should use default for coverage value out of range."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_project = MagicMock()
        mock_project.settings = {
            "min_test_coverage": 150,  # Out of range
        }
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_project("project-123")

        assert settings.min_test_coverage == 80

    def test_get_settings_for_ticket_not_found(self):
        """Should return defaults when ticket is not found."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_ticket("nonexistent-ticket")

        assert settings == DEFAULT_SETTINGS

    def test_get_settings_for_ticket_no_project(self):
        """Should return defaults when ticket has no project."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_ticket = MagicMock()
        mock_ticket.project_id = None
        mock_session.get.return_value = mock_ticket
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_ticket("ticket-123")

        assert settings == DEFAULT_SETTINGS

    def test_get_settings_for_ticket_with_project(self):
        """Should retrieve settings via ticket's project."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_ticket = MagicMock()
        mock_ticket.project_id = "project-456"

        mock_project = MagicMock()
        mock_project.settings = {
            "gate_enforcement_strictness": "bypass",
            "min_test_coverage": 50,
        }

        def mock_get(model, id_):
            from omoi_os.models.ticket import Ticket
            from omoi_os.models.project import Project

            if model == Ticket or (hasattr(model, "__tablename__") and model.__tablename__ == "tickets"):
                return mock_ticket
            if model == Project or (hasattr(model, "__tablename__") and model.__tablename__ == "projects"):
                return mock_project if id_ == "project-456" else None
            # Handle class-based lookup
            if id_ == "ticket-123":
                return mock_ticket
            if id_ == "project-456":
                return mock_project
            return None

        mock_session.get.side_effect = mock_get
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        service = SpecDrivenSettingsService(mock_db)
        settings = service.get_settings_for_ticket("ticket-123")

        assert settings.gate_enforcement_strictness == GateEnforcementStrictness.BYPASS
        assert settings.min_test_coverage == 50
