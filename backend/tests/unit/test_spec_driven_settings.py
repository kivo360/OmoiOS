"""Unit tests for SpecDrivenSettingsService."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from omoi_os.services.spec_driven_settings import (
    SpecDrivenOptionsSchema,
    SpecDrivenSettingsService,
    SettingsChangeLog,
)


class TestSpecDrivenOptionsSchema:
    """Test SpecDrivenOptionsSchema Pydantic model."""

    def test_default_values(self):
        """Should have correct default values."""
        schema = SpecDrivenOptionsSchema()

        assert schema.spec_driven_mode_enabled is False
        assert schema.auto_advance_phases is True
        assert schema.require_approval_gates is False
        assert schema.auto_spawn_tasks is True

    def test_get_defaults_returns_instance(self):
        """get_defaults() should return a schema with defaults."""
        defaults = SpecDrivenOptionsSchema.get_defaults()

        assert isinstance(defaults, SpecDrivenOptionsSchema)
        assert defaults.spec_driven_mode_enabled is False
        assert defaults.auto_advance_phases is True

    def test_custom_values(self):
        """Should accept custom values."""
        schema = SpecDrivenOptionsSchema(
            spec_driven_mode_enabled=True,
            auto_advance_phases=False,
            require_approval_gates=True,
            auto_spawn_tasks=False,
        )

        assert schema.spec_driven_mode_enabled is True
        assert schema.auto_advance_phases is False
        assert schema.require_approval_gates is True
        assert schema.auto_spawn_tasks is False

    def test_model_dump(self):
        """Should serialize to dict correctly."""
        schema = SpecDrivenOptionsSchema(
            spec_driven_mode_enabled=True,
            auto_advance_phases=False,
        )
        dumped = schema.model_dump()

        assert dumped == {
            "spec_driven_mode_enabled": True,
            "auto_advance_phases": False,
            "require_approval_gates": False,
            "auto_spawn_tasks": True,
        }

    def test_extra_fields_forbidden(self):
        """Should reject extra fields."""
        with pytest.raises(Exception):  # ValidationError
            SpecDrivenOptionsSchema(
                spec_driven_mode_enabled=True,
                unknown_field="value",
            )


class TestSettingsChangeLog:
    """Test SettingsChangeLog model."""

    def test_create_change_log(self):
        """Should create change log entry."""
        now = datetime.utcnow()
        log = SettingsChangeLog(
            timestamp=now,
            user_id="user-123",
            old_values={"spec_driven_mode_enabled": False},
            new_values={"spec_driven_mode_enabled": True},
        )

        assert log.timestamp == now
        assert log.user_id == "user-123"
        assert log.old_values["spec_driven_mode_enabled"] is False
        assert log.new_values["spec_driven_mode_enabled"] is True


class TestSpecDrivenSettingsServiceGetSettings:
    """Test SpecDrivenSettingsService.get_settings() method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return SpecDrivenSettingsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_returns_defaults_when_project_not_found(self, service, mock_db):
        """Should return defaults when project doesn't exist."""
        mock_db.get.return_value = None

        result = await service.get_settings("nonexistent-project")

        assert isinstance(result, SpecDrivenOptionsSchema)
        assert result.spec_driven_mode_enabled is False
        assert result.auto_advance_phases is True

    @pytest.mark.asyncio
    async def test_returns_defaults_when_settings_is_none(self, service, mock_db):
        """Should return defaults when project.settings is None."""
        mock_project = MagicMock()
        mock_project.settings = None
        mock_db.get.return_value = mock_project

        result = await service.get_settings("project-123")

        assert isinstance(result, SpecDrivenOptionsSchema)
        assert result.spec_driven_mode_enabled is False

    @pytest.mark.asyncio
    async def test_returns_defaults_when_spec_driven_options_missing(
        self, service, mock_db
    ):
        """Should return defaults when spec_driven_options key is missing."""
        mock_project = MagicMock()
        mock_project.settings = {"some_other_key": "value"}
        mock_db.get.return_value = mock_project

        result = await service.get_settings("project-123")

        assert isinstance(result, SpecDrivenOptionsSchema)
        assert result.spec_driven_mode_enabled is False

    @pytest.mark.asyncio
    async def test_returns_stored_settings(self, service, mock_db):
        """Should return stored settings when they exist."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven_options": {
                "spec_driven_mode_enabled": True,
                "auto_advance_phases": False,
                "require_approval_gates": True,
                "auto_spawn_tasks": False,
            }
        }
        mock_db.get.return_value = mock_project

        result = await service.get_settings("project-123")

        assert result.spec_driven_mode_enabled is True
        assert result.auto_advance_phases is False
        assert result.require_approval_gates is True
        assert result.auto_spawn_tasks is False

    @pytest.mark.asyncio
    async def test_returns_defaults_when_parse_fails(self, service, mock_db):
        """Should return defaults when settings fail to parse."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven_options": {
                "spec_driven_mode_enabled": "not_a_boolean",  # Invalid type
            }
        }
        mock_db.get.return_value = mock_project

        result = await service.get_settings("project-123")

        # Should return defaults, not crash
        assert isinstance(result, SpecDrivenOptionsSchema)
        assert result.spec_driven_mode_enabled is False


class TestSpecDrivenSettingsServiceUpdateSettings:
    """Test SpecDrivenSettingsService.update_settings() method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return SpecDrivenSettingsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_raises_when_project_not_found(self, service, mock_db):
        """Should raise ValueError when project doesn't exist."""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Project not found"):
            await service.update_settings(
                "nonexistent-project",
                SpecDrivenOptionsSchema(spec_driven_mode_enabled=True),
                "user-123",
            )

    @pytest.mark.asyncio
    async def test_persists_settings_to_jsonb(self, service, mock_db):
        """Should persist settings to Project.settings JSONB."""
        mock_project = MagicMock()
        mock_project.settings = None
        mock_db.get.return_value = mock_project

        new_settings = SpecDrivenOptionsSchema(
            spec_driven_mode_enabled=True,
            auto_advance_phases=False,
        )

        result = await service.update_settings("project-123", new_settings, "user-123")

        # Verify settings were updated
        assert mock_project.settings is not None
        assert mock_project.settings["spec_driven_options"] == {
            "spec_driven_mode_enabled": True,
            "auto_advance_phases": False,
            "require_approval_gates": False,
            "auto_spawn_tasks": True,
        }

        # Verify commit was called
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_project)

        # Verify return value
        assert result == new_settings

    @pytest.mark.asyncio
    async def test_logs_old_and_new_values(self, service, mock_db):
        """Should log old and new values in change log."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven_options": {
                "spec_driven_mode_enabled": False,
                "auto_advance_phases": True,
                "require_approval_gates": False,
                "auto_spawn_tasks": True,
            }
        }
        mock_db.get.return_value = mock_project

        new_settings = SpecDrivenOptionsSchema(
            spec_driven_mode_enabled=True,
            auto_advance_phases=False,
        )

        await service.update_settings("project-123", new_settings, "user-456")

        # Verify change log was created
        change_log = mock_project.settings["spec_driven_options_change_log"]
        assert len(change_log) == 1

        log_entry = change_log[0]
        assert log_entry["user_id"] == "user-456"
        assert log_entry["old_values"]["spec_driven_mode_enabled"] is False
        assert log_entry["new_values"]["spec_driven_mode_enabled"] is True
        assert "timestamp" in log_entry

    @pytest.mark.asyncio
    async def test_appends_to_existing_change_log(self, service, mock_db):
        """Should append to existing change log."""
        mock_project = MagicMock()
        existing_log = [
            {
                "timestamp": "2025-01-01T00:00:00",
                "user_id": "user-old",
                "old_values": {},
                "new_values": {},
            }
        ]
        mock_project.settings = {
            "spec_driven_options": {"spec_driven_mode_enabled": False},
            "spec_driven_options_change_log": existing_log,
        }
        mock_db.get.return_value = mock_project

        await service.update_settings(
            "project-123",
            SpecDrivenOptionsSchema(spec_driven_mode_enabled=True),
            "user-new",
        )

        change_log = mock_project.settings["spec_driven_options_change_log"]
        assert len(change_log) == 2
        assert change_log[1]["user_id"] == "user-new"

    @pytest.mark.asyncio
    async def test_updates_project_timestamp(self, service, mock_db):
        """Should update project.updated_at timestamp."""
        mock_project = MagicMock()
        mock_project.settings = {}
        mock_project.updated_at = None
        mock_db.get.return_value = mock_project

        await service.update_settings(
            "project-123",
            SpecDrivenOptionsSchema(),
            "user-123",
        )

        assert mock_project.updated_at is not None


class TestSpecDrivenSettingsServiceGetChangeLog:
    """Test SpecDrivenSettingsService.get_change_log() method."""

    @pytest.fixture
    def mock_db(self):
        """Create mock async database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance."""
        return SpecDrivenSettingsService(db=mock_db)

    @pytest.mark.asyncio
    async def test_returns_empty_when_project_not_found(self, service, mock_db):
        """Should return empty list when project doesn't exist."""
        mock_db.get.return_value = None

        result = await service.get_change_log("nonexistent-project")

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_settings(self, service, mock_db):
        """Should return empty list when no settings."""
        mock_project = MagicMock()
        mock_project.settings = None
        mock_db.get.return_value = mock_project

        result = await service.get_change_log("project-123")

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_change_log_entries(self, service, mock_db):
        """Should return change log entries as SettingsChangeLog objects."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven_options_change_log": [
                {
                    "timestamp": "2025-01-01T00:00:00",
                    "user_id": "user-123",
                    "old_values": {"spec_driven_mode_enabled": False},
                    "new_values": {"spec_driven_mode_enabled": True},
                },
                {
                    "timestamp": "2025-01-02T00:00:00",
                    "user_id": "user-456",
                    "old_values": {"spec_driven_mode_enabled": True},
                    "new_values": {"spec_driven_mode_enabled": False},
                },
            ]
        }
        mock_db.get.return_value = mock_project

        result = await service.get_change_log("project-123")

        assert len(result) == 2
        # Should be in reverse order (most recent first)
        assert result[0].user_id == "user-456"
        assert result[1].user_id == "user-123"

    @pytest.mark.asyncio
    async def test_respects_limit(self, service, mock_db):
        """Should respect the limit parameter."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven_options_change_log": [
                {"timestamp": f"2025-01-0{i}T00:00:00", "user_id": f"user-{i}", "old_values": {}, "new_values": {}}
                for i in range(1, 6)  # 5 entries
            ]
        }
        mock_db.get.return_value = mock_project

        result = await service.get_change_log("project-123", limit=3)

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_handles_invalid_entries_gracefully(self, service, mock_db):
        """Should skip invalid entries without crashing."""
        mock_project = MagicMock()
        mock_project.settings = {
            "spec_driven_options_change_log": [
                {"invalid": "entry"},  # Missing required fields
                {
                    "timestamp": "2025-01-01T00:00:00",
                    "user_id": "user-123",
                    "old_values": {},
                    "new_values": {},
                },
            ]
        }
        mock_db.get.return_value = mock_project

        result = await service.get_change_log("project-123")

        # Should have at least the valid entry
        assert len(result) >= 1
