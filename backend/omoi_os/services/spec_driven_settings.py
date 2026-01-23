"""Spec-driven settings service for reading project-specific settings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from omoi_os.models.project import Project
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService

logger = logging.getLogger(__name__)


class GateEnforcementStrictness(str, Enum):
    """Enforcement strictness levels for phase gates.

    - bypass: Log validation result, always return success
    - lenient: Return warnings but allow transitions
    - strict: Block transition on validation failure
    """
    BYPASS = "bypass"
    LENIENT = "lenient"
    STRICT = "strict"


@dataclass
class SpecDrivenSettings:
    """Container for spec-driven settings values."""

    # Phase gate settings
    gate_enforcement_strictness: GateEnforcementStrictness = GateEnforcementStrictness.STRICT
    min_test_coverage: int = 80

    # Phase progression settings
    auto_phase_progression: bool = True

    # Guardian settings
    guardian_auto_steering: bool = True


# Default settings when none are configured
DEFAULT_SETTINGS = SpecDrivenSettings()


class SpecDrivenSettingsService:
    """Service for reading spec-driven settings from projects.

    Settings are read at operation time (not cached) to ensure fresh values.
    Falls back to defaults if settings are unavailable.
    """

    def __init__(self, db: DatabaseService):
        """Initialize the settings service.

        Args:
            db: DatabaseService instance for database operations
        """
        self.db = db

    def get_settings_for_project(self, project_id: Optional[str]) -> SpecDrivenSettings:
        """Get spec-driven settings for a project.

        Args:
            project_id: The project ID to get settings for

        Returns:
            SpecDrivenSettings with values from project or defaults
        """
        if not project_id:
            logger.debug("No project_id provided, using default settings")
            return DEFAULT_SETTINGS

        with self.db.get_session() as session:
            project = session.get(Project, project_id)
            if not project:
                logger.warning(f"Project {project_id} not found, using default settings")
                return DEFAULT_SETTINGS

            return self._parse_settings(project.settings, project_id)

    def get_settings_for_ticket(self, ticket_id: str) -> SpecDrivenSettings:
        """Get spec-driven settings for a ticket via its project.

        Args:
            ticket_id: The ticket ID to get settings for

        Returns:
            SpecDrivenSettings with values from the ticket's project or defaults
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                logger.warning(f"Ticket {ticket_id} not found, using default settings")
                return DEFAULT_SETTINGS

            project_id = ticket.project_id

        return self.get_settings_for_project(project_id)

    def _parse_settings(
        self,
        settings_dict: Optional[dict[str, Any]],
        project_id: str
    ) -> SpecDrivenSettings:
        """Parse settings dictionary into SpecDrivenSettings object.

        Args:
            settings_dict: Raw settings dictionary from project
            project_id: Project ID for logging

        Returns:
            SpecDrivenSettings with parsed values or defaults
        """
        if not settings_dict:
            logger.debug(f"Project {project_id} has no settings configured, using defaults")
            return DEFAULT_SETTINGS

        # Parse gate enforcement strictness
        strictness_value = settings_dict.get("gate_enforcement_strictness")
        try:
            strictness = GateEnforcementStrictness(strictness_value) if strictness_value else DEFAULT_SETTINGS.gate_enforcement_strictness
        except ValueError:
            logger.warning(
                f"Invalid gate_enforcement_strictness '{strictness_value}' for project {project_id}, "
                f"using default: {DEFAULT_SETTINGS.gate_enforcement_strictness.value}"
            )
            strictness = DEFAULT_SETTINGS.gate_enforcement_strictness

        # Parse min_test_coverage
        min_coverage_value = settings_dict.get("min_test_coverage")
        if min_coverage_value is not None:
            try:
                min_test_coverage = int(min_coverage_value)
                if not 0 <= min_test_coverage <= 100:
                    logger.warning(
                        f"min_test_coverage {min_coverage_value} out of range [0, 100] for project {project_id}, "
                        f"using default: {DEFAULT_SETTINGS.min_test_coverage}"
                    )
                    min_test_coverage = DEFAULT_SETTINGS.min_test_coverage
            except (TypeError, ValueError):
                logger.warning(
                    f"Invalid min_test_coverage '{min_coverage_value}' for project {project_id}, "
                    f"using default: {DEFAULT_SETTINGS.min_test_coverage}"
                )
                min_test_coverage = DEFAULT_SETTINGS.min_test_coverage
        else:
            min_test_coverage = DEFAULT_SETTINGS.min_test_coverage

        # Parse auto_phase_progression
        auto_phase = settings_dict.get("auto_phase_progression")
        if auto_phase is not None:
            auto_phase_progression = bool(auto_phase)
        else:
            auto_phase_progression = DEFAULT_SETTINGS.auto_phase_progression

        # Parse guardian_auto_steering
        auto_steering = settings_dict.get("guardian_auto_steering")
        if auto_steering is not None:
            guardian_auto_steering = bool(auto_steering)
        else:
            guardian_auto_steering = DEFAULT_SETTINGS.guardian_auto_steering

        return SpecDrivenSettings(
            gate_enforcement_strictness=strictness,
            min_test_coverage=min_test_coverage,
            auto_phase_progression=auto_phase_progression,
            guardian_auto_steering=guardian_auto_steering,
        )
