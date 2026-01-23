"""Tests for SpecDrivenSettingsService."""

import pytest

from omoi_os.models.project import Project
from omoi_os.services.database import DatabaseService
from omoi_os.services.spec_driven_settings import (
    SpecDrivenSettings,
    SpecDrivenSettingsService,
    DEFAULT_SETTINGS,
)


@pytest.fixture
def settings_service(db_service: DatabaseService):
    """Create a settings service for testing."""
    return SpecDrivenSettingsService(db=db_service)


@pytest.fixture
def project_with_settings(db_service: DatabaseService) -> Project:
    """Create a project with spec-driven settings configured."""
    with db_service.get_session() as session:
        project = Project(
            name="Test Project with Settings",
            description="Project with custom spec-driven settings",
            settings={
                "spec_driven": {
                    "auto_phase_progression": False,
                    "gate_enforcement_strictness": "strict",
                    "min_test_coverage": 90.0,
                    "guardian_auto_steering": False,
                }
            },
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.expunge(project)
        return project


@pytest.fixture
def project_without_settings(db_service: DatabaseService) -> Project:
    """Create a project without spec-driven settings."""
    with db_service.get_session() as session:
        project = Project(
            name="Test Project without Settings",
            description="Project without spec-driven settings",
            settings=None,
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        session.expunge(project)
        return project


def test_get_settings_returns_custom_values(
    settings_service: SpecDrivenSettingsService,
    project_with_settings: Project,
):
    """Test that get_settings returns custom project values."""
    settings = settings_service.get_settings(project_with_settings.id)

    assert settings.auto_phase_progression is False
    assert settings.gate_enforcement_strictness == "strict"
    assert settings.min_test_coverage == 90.0
    assert settings.guardian_auto_steering is False


def test_get_settings_returns_defaults_for_missing_project(
    settings_service: SpecDrivenSettingsService,
):
    """Test that get_settings returns defaults for non-existent project."""
    settings = settings_service.get_settings("non-existent-project")

    assert settings == DEFAULT_SETTINGS
    assert settings.auto_phase_progression is True
    assert settings.guardian_auto_steering is True


def test_get_settings_returns_defaults_for_unconfigured_project(
    settings_service: SpecDrivenSettingsService,
    project_without_settings: Project,
):
    """Test that get_settings returns defaults for project without settings."""
    settings = settings_service.get_settings(project_without_settings.id)

    assert settings == DEFAULT_SETTINGS


def test_get_guardian_auto_steering(
    settings_service: SpecDrivenSettingsService,
    project_with_settings: Project,
    project_without_settings: Project,
):
    """Test get_guardian_auto_steering convenience method."""
    # Project with auto-steering disabled
    assert settings_service.get_guardian_auto_steering(project_with_settings.id) is False

    # Project without settings (defaults to True)
    assert settings_service.get_guardian_auto_steering(project_without_settings.id) is True


def test_update_settings_updates_values(
    settings_service: SpecDrivenSettingsService,
    project_without_settings: Project,
):
    """Test that update_settings properly updates settings."""
    result = settings_service.update_settings(
        project_without_settings.id,
        guardian_auto_steering=False,
        min_test_coverage=75.0,
    )

    assert result is not None
    assert result.guardian_auto_steering is False
    assert result.min_test_coverage == 75.0
    # Other settings should be defaults
    assert result.auto_phase_progression is True


def test_update_settings_returns_none_for_missing_project(
    settings_service: SpecDrivenSettingsService,
):
    """Test that update_settings returns None for non-existent project."""
    result = settings_service.update_settings(
        "non-existent-project",
        guardian_auto_steering=False,
    )

    assert result is None


def test_partial_settings_merge_with_defaults(
    db_service: DatabaseService,
    settings_service: SpecDrivenSettingsService,
):
    """Test that partial settings are merged with defaults."""
    # Create project with only some settings configured
    with db_service.get_session() as session:
        project = Project(
            name="Test Partial Settings",
            description="Project with partial settings",
            settings={
                "spec_driven": {
                    "guardian_auto_steering": False,
                    # Other settings not configured
                }
            },
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        project_id = project.id
        session.expunge(project)

    settings = settings_service.get_settings(project_id)

    # Configured value
    assert settings.guardian_auto_steering is False
    # Default values for unconfigured settings
    assert settings.auto_phase_progression is True
    assert settings.gate_enforcement_strictness == "standard"
    assert settings.min_test_coverage == 80.0
