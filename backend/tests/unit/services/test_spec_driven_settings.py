"""Unit tests for SpecDrivenSettingsService.

Tests cover:
- Returns defaults when project has no settings
- Returns defaults when spec_driven_options is null
- Update persists correctly to JSONB
- Update logs old/new values
- Handles non-existent project

These are pure unit tests using mocks - no database required.
"""

import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

from omoi_os.models.project import Project
from omoi_os.schemas.spec_driven import (
    SpecDrivenOptionsSchema,
    SpecDrivenOptionsUpdate,
)
from omoi_os.services.spec_driven_settings import (
    SpecDrivenSettingsService,
    ProjectNotFoundError,
    SPEC_DRIVEN_OPTIONS_KEY,
)


def create_mock_project(
    project_id: str = None,
    name: str = "Test Project",
    settings: dict | None = None,
) -> MagicMock:
    """Create a mock Project object."""
    project = MagicMock(spec=Project)
    project.id = project_id or f"project-{uuid4()}"
    project.name = name
    project.settings = settings
    return project


def create_mock_db_service(project: MagicMock | None = None):
    """Create a mock DatabaseService that returns the given project."""
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_query = MagicMock()

    # Configure the query chain
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = project

    mock_session.query.return_value = mock_query
    mock_session.commit = MagicMock()

    @contextmanager
    def mock_get_session():
        yield mock_session

    mock_db.get_session = mock_get_session

    return mock_db, mock_session


@pytest.mark.unit
class TestSpecDrivenSettingsServiceGetSettings:
    """Test get_settings method of SpecDrivenSettingsService."""

    def test_returns_defaults_when_project_has_no_settings(self):
        """UNIT: Should return defaults when project.settings is null."""
        project = create_mock_project(settings=None)
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        result = service.get_settings(project.id)

        assert result.enabled is False
        assert result.strictness == "moderate"
        assert result.require_spec_approval is True
        assert result.min_test_coverage == 80.0

    def test_returns_defaults_when_spec_driven_options_missing(self):
        """UNIT: Should return defaults when spec_driven_options key is missing."""
        project = create_mock_project(settings={"other_key": "other_value"})
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        result = service.get_settings(project.id)

        assert result.enabled is False
        assert result.strictness == "moderate"
        assert result.require_spec_approval is True
        assert result.min_test_coverage == 80.0

    def test_returns_defaults_when_spec_driven_options_is_null(self):
        """UNIT: Should return defaults when spec_driven_options is explicitly null."""
        project = create_mock_project(settings={SPEC_DRIVEN_OPTIONS_KEY: None})
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        result = service.get_settings(project.id)

        assert result.enabled is False
        assert result.strictness == "moderate"

    def test_returns_stored_settings(self):
        """UNIT: Should return stored settings when they exist."""
        stored_settings = {
            SPEC_DRIVEN_OPTIONS_KEY: {
                "enabled": True,
                "strictness": "strict",
                "require_spec_approval": False,
                "min_test_coverage": 95.0,
            }
        }
        project = create_mock_project(settings=stored_settings)
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        result = service.get_settings(project.id)

        assert result.enabled is True
        assert result.strictness == "strict"
        assert result.require_spec_approval is False
        assert result.min_test_coverage == 95.0

    def test_raises_error_for_nonexistent_project(self):
        """UNIT: Should raise ProjectNotFoundError for missing project."""
        mock_db, _ = create_mock_db_service(project=None)
        service = SpecDrivenSettingsService(mock_db)

        with pytest.raises(ProjectNotFoundError) as exc_info:
            service.get_settings("nonexistent-project-id")

        assert "nonexistent-project-id" in str(exc_info.value)

    def test_returns_schema_with_partial_stored_settings(self):
        """UNIT: Should merge stored settings with defaults for missing fields."""
        stored_settings = {
            SPEC_DRIVEN_OPTIONS_KEY: {
                "enabled": True,
                # Other fields missing - should use defaults
            }
        }
        project = create_mock_project(settings=stored_settings)
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        result = service.get_settings(project.id)

        assert result.enabled is True
        assert result.strictness == "moderate"  # default
        assert result.require_spec_approval is True  # default
        assert result.min_test_coverage == 80.0  # default


@pytest.mark.unit
class TestSpecDrivenSettingsServiceUpdateSettings:
    """Test update_settings method of SpecDrivenSettingsService."""

    @patch("omoi_os.services.spec_driven_settings.flag_modified")
    def test_update_persists_to_jsonb(self, mock_flag_modified):
        """UNIT: Update should persist settings to project.settings JSONB."""
        project = create_mock_project(settings=None)
        # Make settings mutable for the test
        project.settings = None
        mock_db, mock_session = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        update = SpecDrivenOptionsUpdate(enabled=True, min_test_coverage=90.0)
        result = service.update_settings(project.id, update)

        assert result.enabled is True
        assert result.min_test_coverage == 90.0
        # Verify commit was called
        mock_session.commit.assert_called_once()
        # Verify flag_modified was called
        mock_flag_modified.assert_called_once_with(project, "settings")

    @patch("omoi_os.services.spec_driven_settings.flag_modified")
    def test_update_preserves_existing_settings(self, mock_flag_modified):
        """UNIT: Update should preserve fields not being updated."""
        initial_settings = {
            SPEC_DRIVEN_OPTIONS_KEY: {
                "enabled": True,
                "strictness": "strict",
                "require_spec_approval": False,
                "min_test_coverage": 95.0,
            }
        }
        project = create_mock_project(settings=initial_settings)
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        # Only update min_test_coverage
        update = SpecDrivenOptionsUpdate(min_test_coverage=85.0)
        result = service.update_settings(project.id, update)

        assert result.enabled is True  # preserved
        assert result.strictness == "strict"  # preserved
        assert result.require_spec_approval is False  # preserved
        assert result.min_test_coverage == 85.0  # updated

    @patch("omoi_os.services.spec_driven_settings.flag_modified")
    def test_update_preserves_other_settings_keys(self, mock_flag_modified):
        """UNIT: Update should preserve other keys in project.settings."""
        initial_settings = {
            "other_key": "other_value",
            SPEC_DRIVEN_OPTIONS_KEY: {"enabled": False},
        }
        project = create_mock_project(settings=initial_settings)
        mock_db, mock_session = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        update = SpecDrivenOptionsUpdate(enabled=True)
        service.update_settings(project.id, update)

        # Verify other_key is still in settings
        assert project.settings.get("other_key") == "other_value"

    @patch("omoi_os.services.spec_driven_settings.flag_modified")
    def test_update_creates_settings_dict_if_null(self, mock_flag_modified):
        """UNIT: Update should create settings dict if project.settings is null."""
        project = create_mock_project(settings=None)
        mock_db, mock_session = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        update = SpecDrivenOptionsUpdate(enabled=True)
        service.update_settings(project.id, update)

        # Verify settings dict was created
        assert project.settings is not None
        assert SPEC_DRIVEN_OPTIONS_KEY in project.settings

    def test_update_raises_error_for_nonexistent_project(self):
        """UNIT: Update should raise ProjectNotFoundError for missing project."""
        mock_db, _ = create_mock_db_service(project=None)
        service = SpecDrivenSettingsService(mock_db)

        update = SpecDrivenOptionsUpdate(enabled=True)
        with pytest.raises(ProjectNotFoundError) as exc_info:
            service.update_settings("nonexistent-project-id", update)

        assert "nonexistent-project-id" in str(exc_info.value)

    @patch("omoi_os.services.spec_driven_settings.flag_modified")
    def test_update_logs_old_and_new_values(self, mock_flag_modified):
        """UNIT: Update should log old and new values for audit."""
        initial_settings = {
            SPEC_DRIVEN_OPTIONS_KEY: {
                "enabled": False,
                "strictness": "moderate",
                "require_spec_approval": True,
                "min_test_coverage": 80.0,
            }
        }
        project = create_mock_project(settings=initial_settings)
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        with patch(
            "omoi_os.services.spec_driven_settings.logger"
        ) as mock_logger:
            update = SpecDrivenOptionsUpdate(enabled=True, strictness="strict")
            service.update_settings(project.id, update)

            # Verify logging was called with old and new values
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "old=" in call_args[0][0]
            assert "new=" in call_args[0][0]

    @patch("omoi_os.services.spec_driven_settings.flag_modified")
    def test_update_all_fields_at_once(self, mock_flag_modified):
        """UNIT: Should be able to update all fields in one call."""
        project = create_mock_project(settings=None)
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        update = SpecDrivenOptionsUpdate(
            enabled=True,
            strictness="strict",
            require_spec_approval=False,
            min_test_coverage=99.0,
        )
        result = service.update_settings(project.id, update)

        assert result.enabled is True
        assert result.strictness == "strict"
        assert result.require_spec_approval is False
        assert result.min_test_coverage == 99.0


@pytest.mark.unit
class TestSpecDrivenSettingsServiceHelpers:
    """Test helper methods of SpecDrivenSettingsService."""

    def test_get_current_settings_dict_with_null_settings(self):
        """UNIT: _get_current_settings_dict should return defaults for null settings."""
        project = create_mock_project(settings=None)
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        result = service._get_current_settings_dict(project)

        assert result == {
            "enabled": False,
            "strictness": "moderate",
            "require_spec_approval": True,
            "min_test_coverage": 80.0,
        }

    def test_get_current_settings_dict_with_empty_settings(self):
        """UNIT: _get_current_settings_dict should return defaults for empty settings."""
        project = create_mock_project(settings={})
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        result = service._get_current_settings_dict(project)

        assert result == {
            "enabled": False,
            "strictness": "moderate",
            "require_spec_approval": True,
            "min_test_coverage": 80.0,
        }

    def test_get_current_settings_dict_merges_with_defaults(self):
        """UNIT: _get_current_settings_dict should merge stored with defaults."""
        project = create_mock_project(
            settings={SPEC_DRIVEN_OPTIONS_KEY: {"enabled": True}}
        )
        mock_db, _ = create_mock_db_service(project)
        service = SpecDrivenSettingsService(mock_db)

        result = service._get_current_settings_dict(project)

        assert result["enabled"] is True
        assert result["strictness"] == "moderate"  # default
        assert result["require_spec_approval"] is True  # default
        assert result["min_test_coverage"] == 80.0  # default

    def test_apply_updates_merges_correctly(self):
        """UNIT: _apply_updates should merge updates with current values."""
        mock_db, _ = create_mock_db_service(None)
        service = SpecDrivenSettingsService(mock_db)

        current = {
            "enabled": False,
            "strictness": "moderate",
            "require_spec_approval": True,
            "min_test_coverage": 80.0,
        }
        updates = SpecDrivenOptionsUpdate(enabled=True, min_test_coverage=90.0)

        result = service._apply_updates(current, updates)

        assert result["enabled"] is True
        assert result["strictness"] == "moderate"  # unchanged
        assert result["require_spec_approval"] is True  # unchanged
        assert result["min_test_coverage"] == 90.0

    def test_apply_updates_with_no_changes(self):
        """UNIT: _apply_updates with empty update should return unchanged values."""
        mock_db, _ = create_mock_db_service(None)
        service = SpecDrivenSettingsService(mock_db)

        current = {
            "enabled": True,
            "strictness": "strict",
            "require_spec_approval": False,
            "min_test_coverage": 95.0,
        }
        updates = SpecDrivenOptionsUpdate()  # No fields set

        result = service._apply_updates(current, updates)

        assert result == current


@pytest.mark.unit
class TestProjectNotFoundError:
    """Test ProjectNotFoundError exception."""

    def test_exception_message(self):
        """UNIT: Exception should contain the provided message."""
        error = ProjectNotFoundError("Project not found: test-123")
        assert str(error) == "Project not found: test-123"

    def test_exception_is_catchable(self):
        """UNIT: Exception should be catchable as Exception."""

        def raise_error():
            raise ProjectNotFoundError("test")

        with pytest.raises(Exception):
            raise_error()

    def test_exception_inherits_from_exception(self):
        """UNIT: ProjectNotFoundError should inherit from Exception."""
        error = ProjectNotFoundError("test")
        assert isinstance(error, Exception)


@pytest.mark.unit
class TestSpecDrivenOptionsKey:
    """Test the SPEC_DRIVEN_OPTIONS_KEY constant."""

    def test_key_value(self):
        """UNIT: Key should have expected value."""
        assert SPEC_DRIVEN_OPTIONS_KEY == "spec_driven_options"
