"""Service for managing spec-driven settings on projects."""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.orm.attributes import flag_modified

from omoi_os.models.project import Project
from omoi_os.schemas.spec_driven import (
    SpecDrivenOptionsSchema,
    SpecDrivenOptionsUpdate,
)
from omoi_os.services.database import DatabaseService

logger = logging.getLogger(__name__)

# Key used in Project.settings JSONB for spec-driven options
SPEC_DRIVEN_OPTIONS_KEY = "spec_driven_options"


class SpecDrivenSettingsService:
    """Service for reading and writing spec-driven settings.

    Settings are stored in the Project.settings JSONB field under the
    'spec_driven_options' key. This service handles:
    - Default values when settings don't exist
    - Validation via Pydantic schemas
    - Audit logging for changes
    """

    def __init__(self, db: DatabaseService):
        """Initialize the service with a database connection.

        Args:
            db: DatabaseService instance for database operations.
        """
        self.db = db

    def get_settings(self, project_id: str) -> SpecDrivenOptionsSchema:
        """Get spec-driven settings for a project.

        Returns default settings if:
        - Project doesn't exist (raises ProjectNotFoundError)
        - Project.settings is null
        - spec_driven_options key doesn't exist in settings

        Args:
            project_id: The ID of the project.

        Returns:
            SpecDrivenOptionsSchema with current or default values.

        Raises:
            ProjectNotFoundError: If the project doesn't exist.
        """
        with self.db.get_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()

            if project is None:
                raise ProjectNotFoundError(f"Project not found: {project_id}")

            # Return defaults if settings or spec_driven_options is null/missing
            if project.settings is None:
                return SpecDrivenOptionsSchema()

            spec_driven_data = project.settings.get(SPEC_DRIVEN_OPTIONS_KEY)
            if spec_driven_data is None:
                return SpecDrivenOptionsSchema()

            # Validate and return the stored settings
            return SpecDrivenOptionsSchema(**spec_driven_data)

    def update_settings(
        self,
        project_id: str,
        updates: SpecDrivenOptionsUpdate,
    ) -> SpecDrivenOptionsSchema:
        """Update spec-driven settings for a project.

        Performs a partial update, only changing fields that are provided.
        Logs old and new values for audit purposes.

        Args:
            project_id: The ID of the project.
            updates: Partial update with fields to change.

        Returns:
            SpecDrivenOptionsSchema with updated values.

        Raises:
            ProjectNotFoundError: If the project doesn't exist.
        """
        with self.db.get_session() as session:
            project = session.query(Project).filter(Project.id == project_id).first()

            if project is None:
                raise ProjectNotFoundError(f"Project not found: {project_id}")

            # Get current settings (or defaults)
            old_settings = self._get_current_settings_dict(project)

            # Apply updates
            new_settings = self._apply_updates(old_settings, updates)

            # Persist to database
            if project.settings is None:
                project.settings = {}

            project.settings[SPEC_DRIVEN_OPTIONS_KEY] = new_settings
            # Force SQLAlchemy to detect the JSONB change
            flag_modified(project, "settings")

            session.commit()

            # Log the change for audit
            logger.info(
                "Updated spec-driven settings for project %s: old=%s, new=%s",
                project_id,
                old_settings,
                new_settings,
            )

            return SpecDrivenOptionsSchema(**new_settings)

    def _get_current_settings_dict(self, project: Project) -> dict[str, Any]:
        """Get current settings as a dictionary, using defaults if needed.

        Args:
            project: The Project model instance.

        Returns:
            Dictionary of current spec-driven settings.
        """
        if project.settings is None:
            return SpecDrivenOptionsSchema().model_dump()

        spec_driven_data = project.settings.get(SPEC_DRIVEN_OPTIONS_KEY)
        if spec_driven_data is None:
            return SpecDrivenOptionsSchema().model_dump()

        # Merge with defaults to ensure all fields exist
        defaults = SpecDrivenOptionsSchema().model_dump()
        defaults.update(spec_driven_data)
        return defaults

    def _apply_updates(
        self,
        current: dict[str, Any],
        updates: SpecDrivenOptionsUpdate,
    ) -> dict[str, Any]:
        """Apply partial updates to current settings.

        Args:
            current: Current settings dictionary.
            updates: Partial update schema.

        Returns:
            New settings dictionary with updates applied.
        """
        result = current.copy()
        update_data = updates.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if value is not None:
                result[key] = value

        return result


class ProjectNotFoundError(Exception):
    """Raised when a project is not found."""

    pass
