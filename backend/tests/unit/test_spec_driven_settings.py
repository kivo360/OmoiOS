"""Tests for SpecDrivenSettingsService."""

import pytest
from unittest.mock import MagicMock, patch

from omoi_os.services.spec_driven_settings import (
    SpecDrivenSettings,
    SpecDrivenSettingsService,
)


class TestSpecDrivenSettings:
    """Tests for the SpecDrivenSettings dataclass."""

    def test_default_values(self):
        """Test default settings values."""
        settings = SpecDrivenSettings()

        assert settings.auto_phase_progression is True
        assert settings.gate_enforcement_strictness == "warn"
        assert settings.min_test_coverage == 80
        assert settings.guardian_auto_steering is True

    def test_custom_values(self):
        """Test custom settings values."""
        settings = SpecDrivenSettings(
            auto_phase_progression=False,
            gate_enforcement_strictness="strict",
            min_test_coverage=90,
            guardian_auto_steering=False,
        )

        assert settings.auto_phase_progression is False
        assert settings.gate_enforcement_strictness == "strict"
        assert settings.min_test_coverage == 90
        assert settings.guardian_auto_steering is False


class TestSpecDrivenSettingsService:
    """Tests for SpecDrivenSettingsService."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database service."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create a settings service with mocked database."""
        return SpecDrivenSettingsService(db=mock_db)

    def test_get_settings_no_project_id(self, service):
        """Test returns defaults when no project_id provided."""
        settings = service.get_settings("")

        assert settings.auto_phase_progression is True
        assert settings.gate_enforcement_strictness == "warn"

    def test_get_settings_project_not_found(self, service, mock_db):
        """Test returns defaults when project not found."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        settings = service.get_settings("project-123")

        assert settings.auto_phase_progression is True
        mock_session.get.assert_called_once()

    def test_get_settings_no_settings_field(self, service, mock_db):
        """Test returns defaults when project has no settings."""
        mock_project = MagicMock()
        mock_project.settings = None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        settings = service.get_settings("project-123")

        assert settings.auto_phase_progression is True

    def test_get_settings_no_spec_driven_key(self, service, mock_db):
        """Test returns defaults when settings has no spec_driven key."""
        mock_project = MagicMock()
        mock_project.settings = {"other_setting": "value"}

        mock_session = MagicMock()
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        settings = service.get_settings("project-123")

        assert settings.auto_phase_progression is True

    def test_get_settings_with_auto_progression_disabled(self, service, mock_db):
        """Test reads auto_phase_progression=False correctly."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven": {
                "auto_phase_progression": False,
            }
        }

        mock_session = MagicMock()
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        settings = service.get_settings("project-123")

        assert settings.auto_phase_progression is False

    def test_get_settings_with_all_settings(self, service, mock_db):
        """Test reads all spec_driven settings correctly."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven": {
                "auto_phase_progression": False,
                "gate_enforcement_strictness": "strict",
                "min_test_coverage": 95,
                "guardian_auto_steering": False,
            }
        }

        mock_session = MagicMock()
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        settings = service.get_settings("project-123")

        assert settings.auto_phase_progression is False
        assert settings.gate_enforcement_strictness == "strict"
        assert settings.min_test_coverage == 95
        assert settings.guardian_auto_steering is False

    def test_get_settings_partial_settings(self, service, mock_db):
        """Test partial settings fall back to defaults."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven": {
                "auto_phase_progression": False,
                # Other settings not specified, should use defaults
            }
        }

        mock_session = MagicMock()
        mock_session.get.return_value = mock_project
        mock_db.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_db.get_session.return_value.__exit__ = MagicMock(return_value=False)

        settings = service.get_settings("project-123")

        assert settings.auto_phase_progression is False
        assert settings.gate_enforcement_strictness == "warn"  # default
        assert settings.min_test_coverage == 80  # default
        assert settings.guardian_auto_steering is True  # default
