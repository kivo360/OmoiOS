"""Spec-driven settings service for project-level configuration.

This service provides access to spec-driven settings stored in the Project.settings JSONB field.
Settings are read fresh at operation time (not cached) to ensure current values.
Falls back to sensible defaults when settings are not configured.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from omoi_os.logging import get_logger
from omoi_os.models.project import Project
from omoi_os.services.database import DatabaseService

logger = get_logger(__name__)


@dataclass
class SpecDrivenSettings:
    """Spec-driven settings for a project.

    These settings control autonomous behavior of the spec-driven workflow:
    - auto_phase_progression: Whether to automatically advance tickets between phases
    - gate_enforcement_strictness: How strictly to enforce phase gate requirements
    - min_test_coverage: Minimum test coverage percentage required
    - guardian_auto_steering: Whether Guardian can automatically execute interventions
    """

    # Phase progression settings
    auto_phase_progression: bool = True

    # Phase gate settings
    gate_enforcement_strictness: str = "standard"  # "strict", "standard", "lenient"
    min_test_coverage: float = 80.0

    # Guardian settings
    guardian_auto_steering: bool = True


# Default settings instance (used when no project settings exist)
DEFAULT_SETTINGS = SpecDrivenSettings()


class SpecDrivenSettingsService:
    """Service for accessing project-level spec-driven settings.

    Settings are stored in the Project.settings JSONB field under the
    "spec_driven" key. This service reads settings fresh from the database
    at each access to ensure current values.

    Example settings structure in Project.settings:
    {
        "spec_driven": {
            "auto_phase_progression": true,
            "gate_enforcement_strictness": "standard",
            "min_test_coverage": 80.0,
            "guardian_auto_steering": true
        }
    }
    """

    def __init__(self, db: DatabaseService):
        """Initialize the settings service.

        Args:
            db: DatabaseService instance for database operations
        """
        self.db = db

    def get_settings(self, project_id: str) -> SpecDrivenSettings:
        """Get spec-driven settings for a project.

        Settings are read fresh from the database (not cached) to ensure
        the most current values are used. Falls back to defaults when:
        - Project not found
        - Project has no settings configured
        - Settings are partially configured (missing keys use defaults)

        Args:
            project_id: The project ID to get settings for

        Returns:
            SpecDrivenSettings instance with project settings or defaults
        """
        with self.db.get_session() as session:
            project = session.get(Project, project_id)

            if not project:
                logger.debug(
                    "Project not found, using default settings",
                    project_id=project_id,
                )
                return DEFAULT_SETTINGS

            settings_data = project.settings or {}
            spec_driven_data = settings_data.get("spec_driven", {})

            if not spec_driven_data:
                logger.debug(
                    "No spec-driven settings configured, using defaults",
                    project_id=project_id,
                )
                return DEFAULT_SETTINGS

            # Merge with defaults for any missing keys
            return SpecDrivenSettings(
                auto_phase_progression=spec_driven_data.get(
                    "auto_phase_progression",
                    DEFAULT_SETTINGS.auto_phase_progression,
                ),
                gate_enforcement_strictness=spec_driven_data.get(
                    "gate_enforcement_strictness",
                    DEFAULT_SETTINGS.gate_enforcement_strictness,
                ),
                min_test_coverage=spec_driven_data.get(
                    "min_test_coverage",
                    DEFAULT_SETTINGS.min_test_coverage,
                ),
                guardian_auto_steering=spec_driven_data.get(
                    "guardian_auto_steering",
                    DEFAULT_SETTINGS.guardian_auto_steering,
                ),
            )

    def update_settings(
        self,
        project_id: str,
        **kwargs: Any,
    ) -> Optional[SpecDrivenSettings]:
        """Update spec-driven settings for a project.

        Only updates the provided settings, leaving others unchanged.

        Args:
            project_id: The project ID to update settings for
            **kwargs: Settings to update (auto_phase_progression,
                      gate_enforcement_strictness, min_test_coverage,
                      guardian_auto_steering)

        Returns:
            Updated SpecDrivenSettings if successful, None if project not found
        """
        valid_keys = {
            "auto_phase_progression",
            "gate_enforcement_strictness",
            "min_test_coverage",
            "guardian_auto_steering",
        }

        # Filter to only valid settings keys
        updates = {k: v for k, v in kwargs.items() if k in valid_keys}

        if not updates:
            logger.warning(
                "No valid settings to update",
                project_id=project_id,
                provided_keys=list(kwargs.keys()),
            )
            return self.get_settings(project_id)

        with self.db.get_session() as session:
            project = session.get(Project, project_id)

            if not project:
                logger.warning(
                    "Project not found for settings update",
                    project_id=project_id,
                )
                return None

            # Initialize settings if needed
            if project.settings is None:
                project.settings = {}

            # Initialize spec_driven section if needed
            if "spec_driven" not in project.settings:
                project.settings["spec_driven"] = {}

            # Update the settings
            project.settings["spec_driven"].update(updates)

            # Flag as modified for SQLAlchemy to detect the change
            from sqlalchemy.orm import attributes
            attributes.flag_modified(project, "settings")

            session.commit()

            logger.info(
                "Updated spec-driven settings",
                project_id=project_id,
                updated_keys=list(updates.keys()),
            )

        return self.get_settings(project_id)

    def get_guardian_auto_steering(self, project_id: str) -> bool:
        """Get the guardian_auto_steering setting for a project.

        Convenience method for checking if Guardian should auto-execute
        interventions for this project.

        Args:
            project_id: The project ID to check

        Returns:
            True if auto-steering is enabled, False otherwise
        """
        settings = self.get_settings(project_id)
        return settings.guardian_auto_steering


# Singleton instance (lazy initialization)
_settings_service: Optional[SpecDrivenSettingsService] = None


def get_spec_driven_settings_service(
    db: Optional[DatabaseService] = None,
) -> SpecDrivenSettingsService:
    """Get or create the singleton spec-driven settings service.

    Args:
        db: DatabaseService instance (required for first initialization)

    Returns:
        SpecDrivenSettingsService singleton instance

    Raises:
        ValueError: If db is not provided on first initialization
    """
    global _settings_service

    if _settings_service is None:
        if db is None:
            raise ValueError(
                "Must provide db for first initialization of SpecDrivenSettingsService"
            )
        _settings_service = SpecDrivenSettingsService(db=db)

    return _settings_service
