"""Spec-driven settings service for reading project-level spec-driven workflow settings.

This service provides access to spec-driven workflow settings stored in the
Project model's settings JSONB field. It handles:
- Reading auto_phase_progression setting
- Reading gate_enforcement_strictness setting
- Reading min_test_coverage setting
- Reading guardian_auto_steering setting

Default values are provided when settings are missing to preserve backward compatibility.
"""

from dataclasses import dataclass
from typing import Optional

from omoi_os.logging import get_logger
from omoi_os.models.project import Project
from omoi_os.services.database import DatabaseService

logger = get_logger(__name__)


@dataclass
class SpecDrivenSettings:
    """Settings for spec-driven workflow behavior.

    Attributes:
        auto_phase_progression: Whether to auto-advance tickets through phases.
            When False, tickets require manual advancement. Default: True
        gate_enforcement_strictness: How strictly to enforce phase gates.
            Options: 'strict', 'warn', 'none'. Default: 'warn'
        min_test_coverage: Minimum test coverage percentage required. Default: 80
        guardian_auto_steering: Whether guardian can auto-steer agents.
            When False, guardian logs only. Default: True
    """
    auto_phase_progression: bool = True
    gate_enforcement_strictness: str = "warn"
    min_test_coverage: int = 80
    guardian_auto_steering: bool = True


class SpecDrivenSettingsService:
    """Service for reading spec-driven workflow settings from project configuration.

    This service reads settings from the Project model's settings JSONB field
    under the 'spec_driven' key. Settings are read fresh on each call (not cached)
    to ensure configuration changes take effect immediately.

    Example project settings structure:
    {
        "spec_driven": {
            "auto_phase_progression": true,
            "gate_enforcement_strictness": "strict",
            "min_test_coverage": 90,
            "guardian_auto_steering": false
        }
    }
    """

    def __init__(self, db: DatabaseService):
        """Initialize the settings service.

        Args:
            db: Database service for project queries
        """
        self.db = db

    def get_settings(self, project_id: str) -> SpecDrivenSettings:
        """Get spec-driven settings for a project.

        Reads settings from the project's settings JSONB field.
        Returns default values if the project doesn't exist or settings are missing.

        Args:
            project_id: The project ID to get settings for

        Returns:
            SpecDrivenSettings with project settings or defaults
        """
        if not project_id:
            logger.debug("No project_id provided, using default settings")
            return SpecDrivenSettings()

        with self.db.get_session() as session:
            project = session.get(Project, project_id)

            if not project:
                logger.warning(
                    "Project not found, using default settings",
                    project_id=project_id,
                )
                return SpecDrivenSettings()

            return self._extract_settings(project.settings, project_id)

    async def get_settings_async(self, project_id: str) -> SpecDrivenSettings:
        """Get spec-driven settings for a project (async version).

        Reads settings from the project's settings JSONB field.
        Returns default values if the project doesn't exist or settings are missing.

        Args:
            project_id: The project ID to get settings for

        Returns:
            SpecDrivenSettings with project settings or defaults
        """
        from sqlalchemy import select

        if not project_id:
            logger.debug("No project_id provided, using default settings")
            return SpecDrivenSettings()

        async with self.db.get_async_session() as session:
            result = await session.execute(
                select(Project).filter(Project.id == project_id)
            )
            project = result.scalar_one_or_none()

            if not project:
                logger.warning(
                    "Project not found, using default settings",
                    project_id=project_id,
                )
                return SpecDrivenSettings()

            return self._extract_settings(project.settings, project_id)

    def _extract_settings(
        self,
        project_settings: Optional[dict],
        project_id: str
    ) -> SpecDrivenSettings:
        """Extract spec-driven settings from project settings dict.

        Args:
            project_settings: The project's settings JSONB field value
            project_id: Project ID for logging

        Returns:
            SpecDrivenSettings extracted from project settings or defaults
        """
        if not project_settings:
            logger.debug(
                "No project settings configured, using defaults",
                project_id=project_id,
            )
            return SpecDrivenSettings()

        spec_driven = project_settings.get("spec_driven", {})

        if not spec_driven:
            logger.debug(
                "No spec_driven settings configured, using defaults",
                project_id=project_id,
            )
            return SpecDrivenSettings()

        settings = SpecDrivenSettings(
            auto_phase_progression=spec_driven.get("auto_phase_progression", True),
            gate_enforcement_strictness=spec_driven.get(
                "gate_enforcement_strictness", "warn"
            ),
            min_test_coverage=spec_driven.get("min_test_coverage", 80),
            guardian_auto_steering=spec_driven.get("guardian_auto_steering", True),
        )

        logger.debug(
            "Loaded spec-driven settings",
            project_id=project_id,
            auto_phase_progression=settings.auto_phase_progression,
            gate_enforcement_strictness=settings.gate_enforcement_strictness,
            min_test_coverage=settings.min_test_coverage,
            guardian_auto_steering=settings.guardian_auto_steering,
        )

        return settings


# Module-level singleton instance (lazy initialization)
_spec_driven_settings_service: Optional[SpecDrivenSettingsService] = None


def get_spec_driven_settings_service(
    db: Optional[DatabaseService] = None,
) -> SpecDrivenSettingsService:
    """Get or create the singleton spec-driven settings service.

    Args:
        db: Database service (required for first initialization)

    Returns:
        SpecDrivenSettingsService singleton instance

    Raises:
        ValueError: If db is not provided for first initialization
    """
    global _spec_driven_settings_service

    if _spec_driven_settings_service is None:
        if db is None:
            raise ValueError(
                "Must provide db for first initialization of SpecDrivenSettingsService"
            )
        _spec_driven_settings_service = SpecDrivenSettingsService(db=db)

    return _spec_driven_settings_service
