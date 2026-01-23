"""Service for managing spec-driven development settings.

This service handles reading and writing spec-driven settings from the
Project.settings JSONB field. Settings are stored under the
'spec_driven_options' key.

Usage:
    service = SpecDrivenSettingsService(db_session)
    settings = await service.get_settings(project_id)
    updated = await service.update_settings(project_id, new_settings, user_id)
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from omoi_os.logging import get_logger
from omoi_os.models.project import Project
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


class SpecDrivenOptionsSchema(BaseModel):
    """Schema for spec-driven development settings.

    These settings control how spec-driven development workflows behave
    for a project. They are stored in Project.settings JSONB field
    under the 'spec_driven_options' key.
    """

    spec_driven_mode_enabled: bool = Field(
        default=False,
        description="Enable spec-driven workflow mode for this project. "
        "When enabled, tickets can use spec-driven workflow.",
    )
    auto_advance_phases: bool = Field(
        default=True,
        description="Automatically advance through spec phases (EXPLORE → "
        "REQUIREMENTS → DESIGN → TASKS → SYNC) without manual intervention.",
    )
    require_approval_gates: bool = Field(
        default=False,
        description="Require manual approval at phase gates before advancing. "
        "When True, phases pause and wait for user approval.",
    )
    auto_spawn_tasks: bool = Field(
        default=True,
        description="Automatically spawn implementation tasks after SYNC phase. "
        "When False, tasks must be spawned manually.",
    )

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def get_defaults(cls) -> "SpecDrivenOptionsSchema":
        """Return default settings instance."""
        return cls()


class SettingsChangeLog(BaseModel):
    """Record of a settings change for audit logging."""

    timestamp: datetime
    user_id: str
    old_values: dict
    new_values: dict


class SpecDrivenSettingsService:
    """Service for reading/writing spec-driven settings from Project.settings.

    This service encapsulates all settings persistence logic. It is designed
    to be used by API endpoints and other services (PhaseProgressionService, etc.).
    """

    def __init__(self, db: AsyncSession):
        """Initialize the service.

        Args:
            db: Async database session for queries.
        """
        self.db = db

    async def get_settings(self, project_id: str) -> SpecDrivenOptionsSchema:
        """Get spec-driven settings for a project.

        Returns the settings if they exist, otherwise returns defaults.

        Args:
            project_id: The project ID to get settings for.

        Returns:
            SpecDrivenOptionsSchema with current settings or defaults.
        """
        project = await self.db.get(Project, project_id)

        if not project:
            logger.debug(
                "Project not found, returning default settings",
                project_id=project_id,
            )
            return SpecDrivenOptionsSchema.get_defaults()

        if not project.settings:
            logger.debug(
                "Project has no settings, returning defaults",
                project_id=project_id,
            )
            return SpecDrivenOptionsSchema.get_defaults()

        options = project.settings.get("spec_driven_options")
        if not options:
            logger.debug(
                "No spec_driven_options in settings, returning defaults",
                project_id=project_id,
            )
            return SpecDrivenOptionsSchema.get_defaults()

        try:
            return SpecDrivenOptionsSchema(**options)
        except Exception as e:
            logger.warning(
                "Failed to parse spec_driven_options, returning defaults",
                project_id=project_id,
                error=str(e),
            )
            return SpecDrivenOptionsSchema.get_defaults()

    async def update_settings(
        self,
        project_id: str,
        settings: SpecDrivenOptionsSchema,
        user_id: str,
    ) -> SpecDrivenOptionsSchema:
        """Update spec-driven settings for a project.

        Persists the settings to the Project.settings JSONB field and logs
        the change with timestamp, user_id, and old/new values.

        Args:
            project_id: The project ID to update settings for.
            settings: The new settings to persist.
            user_id: The ID of the user making the change.

        Returns:
            The updated SpecDrivenOptionsSchema.

        Raises:
            ValueError: If the project is not found.
        """
        project = await self.db.get(Project, project_id)

        if not project:
            raise ValueError(f"Project not found: {project_id}")

        # Get old settings for logging
        old_settings = await self.get_settings(project_id)
        old_values = old_settings.model_dump()

        # Prepare new settings
        new_values = settings.model_dump()

        # Initialize settings dict if needed
        if project.settings is None:
            project.settings = {}

        # Get or initialize change log
        change_log = project.settings.get("spec_driven_options_change_log", [])

        # Create change log entry
        change_entry = SettingsChangeLog(
            timestamp=utc_now(),
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
        )
        change_log.append(change_entry.model_dump(mode="json"))

        # Update settings - create a new dict to trigger SQLAlchemy change detection
        updated_settings = dict(project.settings)
        updated_settings["spec_driven_options"] = new_values
        updated_settings["spec_driven_options_change_log"] = change_log
        project.settings = updated_settings

        # Update timestamp
        project.updated_at = utc_now()

        # Commit the changes
        await self.db.commit()
        await self.db.refresh(project)

        logger.info(
            "Updated spec-driven settings",
            project_id=project_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
        )

        return settings

    async def get_change_log(
        self, project_id: str, limit: int = 50
    ) -> list[SettingsChangeLog]:
        """Get the change log for spec-driven settings.

        Args:
            project_id: The project ID to get change log for.
            limit: Maximum number of entries to return.

        Returns:
            List of SettingsChangeLog entries, most recent first.
        """
        project = await self.db.get(Project, project_id)

        if not project or not project.settings:
            return []

        change_log = project.settings.get("spec_driven_options_change_log", [])

        # Convert to SettingsChangeLog objects and reverse for most recent first
        entries = []
        for entry in reversed(change_log[-limit:]):
            try:
                entries.append(SettingsChangeLog(**entry))
            except Exception as e:
                logger.warning(
                    "Failed to parse change log entry",
                    project_id=project_id,
                    error=str(e),
                )

        return entries
