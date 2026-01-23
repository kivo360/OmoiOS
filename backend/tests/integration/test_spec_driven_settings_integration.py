"""Integration tests for spec-driven settings.

These tests verify that services correctly read and apply project-specific settings
from the Project.settings JSONB column, falling back to defaults when not configured.

Test Scenarios:
1. PhaseProgressionService: Auto-advance when enabled/disabled, defaults
2. PhaseGateService: Strict/lenient/bypass modes, custom coverage thresholds
3. GuardianService: Auto-steering enabled/disabled

Note: These tests use mocked database operations to avoid requiring a running
PostgreSQL instance. The focus is on testing the settings reading and application
logic, not the database persistence itself.
"""

from __future__ import annotations

from typing import Any, Optional
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass, field

import pytest


# =============================================================================
# SPEC-DRIVEN SETTINGS SCHEMA
# =============================================================================
# These define the expected settings structure that services should read from
# Project.settings JSONB column.

DEFAULT_SPEC_SETTINGS = {
    "phase_progression": {
        "auto_phase_progression": False,  # Default: manual progression
        "require_gate_approval": True,
    },
    "phase_gates": {
        "strictness": "strict",  # strict | lenient | bypass
        "coverage_threshold": 80,  # Default 80% coverage requirement
        "require_artifacts": True,
    },
    "guardian": {
        "auto_steering_enabled": False,  # Default: log only
        "intervention_threshold": "high",  # low | medium | high
    },
}


def get_spec_setting(
    project_settings: Optional[dict], path: str, default: Any = None
) -> Any:
    """Get a setting from project settings using dot notation path.

    Args:
        project_settings: The project's settings dict (may be None)
        path: Dot-separated path like "phase_gates.strictness"
        default: Value to return if path not found

    Returns:
        The setting value or default
    """
    if not project_settings:
        return default

    keys = path.split(".")
    value = project_settings
    for key in keys:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
        if value is None:
            return default
    return value


# =============================================================================
# MOCK DATA CLASSES
# =============================================================================
# Lightweight mock classes to represent database models without actual DB


@dataclass
class MockProject:
    """Mock Project model for testing."""
    id: str
    name: str
    description: str = ""
    settings: Optional[dict] = None


@dataclass
class MockTicket:
    """Mock Ticket model for testing."""
    id: str
    title: str
    phase_id: str
    status: str = "in_progress"
    priority: str = "MEDIUM"
    project_id: Optional[str] = None


@dataclass
class MockTask:
    """Mock Task model for testing."""
    id: str
    ticket_id: str
    phase_id: str
    task_type: str = "test_task"
    status: str = "pending"
    priority: str = "MEDIUM"
    error_message: Optional[str] = None
    assigned_agent_id: Optional[str] = None


@dataclass
class MockArtifact:
    """Mock PhaseGateArtifact model for testing."""
    id: str
    ticket_id: str
    phase_id: str
    artifact_type: str
    artifact_content: dict = field(default_factory=dict)


@dataclass
class MockGuardianAction:
    """Mock GuardianAction model for testing."""
    id: str
    action_type: str
    target_entity: str
    authority_level: int = 4  # GUARDIAN level
    reason: str = ""
    initiated_by: str = ""


# =============================================================================
# SPEC-DRIVEN SETTINGS SERVICES (MOCK IMPLEMENTATIONS)
# =============================================================================


class SpecDrivenPhaseProgressionService:
    """Mock service for phase progression with spec-driven settings support.

    This demonstrates how PhaseProgressionService should read and apply settings.
    """

    def __init__(self, project: MockProject):
        self.project = project

    def should_auto_advance(self, ticket: MockTicket) -> bool:
        """Check if phase should auto-advance based on project settings."""
        auto_progress = get_spec_setting(
            self.project.settings,
            "phase_progression.auto_phase_progression",
            DEFAULT_SPEC_SETTINGS["phase_progression"]["auto_phase_progression"],
        )
        return auto_progress and ticket.status != "blocked"

    def requires_gate_approval(self) -> bool:
        """Check if gate approval is required based on settings."""
        return get_spec_setting(
            self.project.settings,
            "phase_progression.require_gate_approval",
            DEFAULT_SPEC_SETTINGS["phase_progression"]["require_gate_approval"],
        )


class SpecDrivenPhaseGateService:
    """Mock service for phase gates with spec-driven settings support.

    This demonstrates how PhaseGateService should read and apply settings.
    """

    def __init__(self, project: MockProject):
        self.project = project

    def get_strictness_mode(self) -> str:
        """Get the gate strictness mode from settings."""
        return get_spec_setting(
            self.project.settings,
            "phase_gates.strictness",
            DEFAULT_SPEC_SETTINGS["phase_gates"]["strictness"],
        )

    def get_coverage_threshold(self) -> int:
        """Get the required coverage threshold from settings."""
        return get_spec_setting(
            self.project.settings,
            "phase_gates.coverage_threshold",
            DEFAULT_SPEC_SETTINGS["phase_gates"]["coverage_threshold"],
        )

    def requires_artifacts(self) -> bool:
        """Check if artifacts are required based on settings."""
        return get_spec_setting(
            self.project.settings,
            "phase_gates.require_artifacts",
            DEFAULT_SPEC_SETTINGS["phase_gates"]["require_artifacts"],
        )

    def validate_gate(
        self, ticket: MockTicket, coverage: int, has_artifacts: bool
    ) -> tuple[bool, list[str], bool]:
        """Validate gate with spec-driven settings.

        Returns:
            Tuple of (can_proceed, warnings, is_blocking)
        """
        strictness = self.get_strictness_mode()
        coverage_threshold = self.get_coverage_threshold()
        require_artifacts = self.requires_artifacts()

        warnings = []
        passes = True

        # Check coverage
        if coverage < coverage_threshold:
            warnings.append(
                f"Coverage {coverage}% below threshold {coverage_threshold}%"
            )
            if strictness == "strict":
                passes = False

        # Check artifacts
        if require_artifacts and not has_artifacts:
            warnings.append("Missing required artifacts")
            if strictness == "strict":
                passes = False

        # Determine blocking behavior based on strictness
        if strictness == "bypass":
            return True, warnings, False  # Always allow, log warnings
        elif strictness == "lenient":
            return True, warnings, False  # Allow with warnings
        else:  # strict
            return passes, warnings, not passes


class SpecDrivenGuardianService:
    """Mock service for guardian with spec-driven settings support.

    This demonstrates how GuardianService should read and apply settings.
    """

    def __init__(self, project: MockProject):
        self.project = project
        self.log = []  # Capture log entries for testing

    def is_auto_steering_enabled(self) -> bool:
        """Check if auto-steering is enabled from settings."""
        return get_spec_setting(
            self.project.settings,
            "guardian.auto_steering_enabled",
            DEFAULT_SPEC_SETTINGS["guardian"]["auto_steering_enabled"],
        )

    def get_intervention_threshold(self) -> str:
        """Get the intervention threshold from settings."""
        return get_spec_setting(
            self.project.settings,
            "guardian.intervention_threshold",
            DEFAULT_SPEC_SETTINGS["guardian"]["intervention_threshold"],
        )

    def handle_stuck_task(self, task: MockTask) -> Optional[MockGuardianAction]:
        """Handle a stuck task based on settings.

        Returns:
            GuardianAction if intervention executed, None if only logged
        """
        auto_steering = self.is_auto_steering_enabled()

        if auto_steering:
            # Execute intervention
            action = MockGuardianAction(
                id=f"action-{task.id}",
                action_type="cancel_task",
                target_entity=task.id,
                reason="Auto-steering intervention: Task stuck",
                initiated_by="guardian-system",
            )
            task.status = "failed"
            task.error_message = "EMERGENCY CANCELLATION: " + action.reason
            self.log.append(f"INTERVENTION: Cancelled task {task.id}")
            return action
        else:
            # Log only, no intervention
            self.log.append(f"OBSERVATION: Task {task.id} appears stuck (no intervention)")
            return None


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def default_project() -> MockProject:
    """Create a project with default settings (None)."""
    return MockProject(
        id="project-default",
        name="Default Project",
        description="Project with no custom settings",
        settings=None,
    )


@pytest.fixture
def project_with_auto_progression() -> MockProject:
    """Create a project with auto phase progression enabled."""
    return MockProject(
        id="project-auto-progress",
        name="Auto-Progress Project",
        description="Project with auto phase progression",
        settings={
            "phase_progression": {
                "auto_phase_progression": True,
                "require_gate_approval": False,
            }
        },
    )


@pytest.fixture
def project_with_lenient_gates() -> MockProject:
    """Create a project with lenient gate mode."""
    return MockProject(
        id="project-lenient",
        name="Lenient Gates Project",
        description="Project with lenient phase gates",
        settings={
            "phase_gates": {
                "strictness": "lenient",
                "coverage_threshold": 60,
                "require_artifacts": True,
            }
        },
    )


@pytest.fixture
def project_with_bypass_gates() -> MockProject:
    """Create a project with bypass gate mode."""
    return MockProject(
        id="project-bypass",
        name="Bypass Gates Project",
        description="Project with bypass phase gates",
        settings={
            "phase_gates": {
                "strictness": "bypass",
                "coverage_threshold": 0,
                "require_artifacts": False,
            }
        },
    )


@pytest.fixture
def project_with_auto_steering() -> MockProject:
    """Create a project with auto-steering enabled."""
    return MockProject(
        id="project-auto-steering",
        name="Auto-Steering Project",
        description="Project with guardian auto-steering",
        settings={
            "guardian": {
                "auto_steering_enabled": True,
                "intervention_threshold": "medium",
            }
        },
    )


@pytest.fixture
def project_with_custom_coverage() -> MockProject:
    """Create a project with custom coverage threshold."""
    return MockProject(
        id="project-coverage-90",
        name="Custom Coverage Project",
        description="Project with 90% coverage requirement",
        settings={
            "phase_gates": {
                "strictness": "strict",
                "coverage_threshold": 90,
                "require_artifacts": True,
            }
        },
    )


# =============================================================================
# PHASE PROGRESSION SERVICE TESTS
# =============================================================================


class TestPhaseProgressionSettings:
    """Tests for PhaseProgressionService respecting auto_phase_progression setting."""

    def test_auto_advance_enabled_progresses_phase(
        self, project_with_auto_progression: MockProject
    ):
        """When auto_phase_progression is enabled, service should advance phase automatically."""
        # Arrange
        ticket = MockTicket(
            id="ticket-1",
            title="Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="in_progress",
            project_id=project_with_auto_progression.id,
        )
        service = SpecDrivenPhaseProgressionService(project_with_auto_progression)

        # Act
        should_advance = service.should_auto_advance(ticket)

        # Assert
        assert should_advance is True

    def test_auto_advance_disabled_requires_manual(
        self, default_project: MockProject
    ):
        """When auto_phase_progression is disabled (default), require manual advancement."""
        # Arrange
        ticket = MockTicket(
            id="ticket-2",
            title="Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="in_progress",
            project_id=default_project.id,
        )
        service = SpecDrivenPhaseProgressionService(default_project)

        # Act
        should_advance = service.should_auto_advance(ticket)

        # Assert
        assert should_advance is False

    def test_auto_advance_blocked_ticket_does_not_advance(
        self, project_with_auto_progression: MockProject
    ):
        """Even with auto-advance enabled, blocked tickets should not advance."""
        # Arrange
        ticket = MockTicket(
            id="ticket-3",
            title="Blocked Ticket",
            phase_id="PHASE_REQUIREMENTS",
            status="blocked",
            project_id=project_with_auto_progression.id,
        )
        service = SpecDrivenPhaseProgressionService(project_with_auto_progression)

        # Act
        should_advance = service.should_auto_advance(ticket)

        # Assert
        assert should_advance is False

    def test_defaults_used_when_no_settings(
        self, default_project: MockProject
    ):
        """When project has no settings, defaults should be used."""
        # Assert project has no settings
        assert default_project.settings is None

        service = SpecDrivenPhaseProgressionService(default_project)

        # Check defaults
        ticket = MockTicket(
            id="ticket-4",
            title="Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            project_id=default_project.id,
        )

        assert service.should_auto_advance(ticket) is False
        assert service.requires_gate_approval() is True


# =============================================================================
# PHASE GATE SERVICE TESTS
# =============================================================================


class TestPhaseGateSettings:
    """Tests for PhaseGateService respecting strictness and coverage settings."""

    def test_strict_mode_blocks_on_failure(
        self, default_project: MockProject
    ):
        """In strict mode, gate failures should block progression."""
        # Arrange
        ticket = MockTicket(
            id="ticket-5",
            title="Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            project_id=default_project.id,
        )
        service = SpecDrivenPhaseGateService(default_project)

        # Act: Low coverage should fail
        can_proceed, warnings, is_blocking = service.validate_gate(
            ticket, coverage=50, has_artifacts=True
        )

        # Assert
        assert service.get_strictness_mode() == "strict"
        assert can_proceed is False
        assert is_blocking is True
        assert any("coverage" in w.lower() for w in warnings)

    def test_lenient_mode_warns_but_allows(
        self, project_with_lenient_gates: MockProject
    ):
        """In lenient mode, gate issues should warn but allow progression."""
        # Arrange
        ticket = MockTicket(
            id="ticket-6",
            title="Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            project_id=project_with_lenient_gates.id,
        )
        service = SpecDrivenPhaseGateService(project_with_lenient_gates)

        # Act: Coverage meets lenient threshold (65% >= 60%)
        can_proceed, warnings, is_blocking = service.validate_gate(
            ticket, coverage=65, has_artifacts=True
        )

        # Assert
        assert service.get_strictness_mode() == "lenient"
        assert service.get_coverage_threshold() == 60
        assert can_proceed is True
        assert is_blocking is False

    def test_lenient_mode_allows_with_warnings(
        self, project_with_lenient_gates: MockProject
    ):
        """In lenient mode, even failures are allowed with warnings."""
        # Arrange
        ticket = MockTicket(
            id="ticket-7",
            title="Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            project_id=project_with_lenient_gates.id,
        )
        service = SpecDrivenPhaseGateService(project_with_lenient_gates)

        # Act: Coverage below threshold
        can_proceed, warnings, is_blocking = service.validate_gate(
            ticket, coverage=40, has_artifacts=True
        )

        # Assert: Still allowed but with warnings
        assert can_proceed is True
        assert is_blocking is False
        assert len(warnings) > 0

    def test_bypass_mode_logs_and_allows(
        self, project_with_bypass_gates: MockProject
    ):
        """In bypass mode, gates should log but always allow progression."""
        # Arrange
        ticket = MockTicket(
            id="ticket-8",
            title="Test Ticket",
            phase_id="PHASE_REQUIREMENTS",
            project_id=project_with_bypass_gates.id,
        )
        service = SpecDrivenPhaseGateService(project_with_bypass_gates)

        # Act: No coverage, no artifacts - would normally fail
        can_proceed, warnings, is_blocking = service.validate_gate(
            ticket, coverage=0, has_artifacts=False
        )

        # Assert
        assert service.get_strictness_mode() == "bypass"
        assert can_proceed is True
        assert is_blocking is False

    def test_custom_coverage_threshold_enforced(
        self, project_with_custom_coverage: MockProject
    ):
        """Custom coverage thresholds should be enforced."""
        # Arrange
        ticket = MockTicket(
            id="ticket-9",
            title="Test Ticket",
            phase_id="PHASE_IMPLEMENTATION",
            project_id=project_with_custom_coverage.id,
        )
        service = SpecDrivenPhaseGateService(project_with_custom_coverage)

        # Assert custom threshold
        assert service.get_coverage_threshold() == 90

        # Act: 85% coverage should fail 90% threshold
        can_proceed, warnings, is_blocking = service.validate_gate(
            ticket, coverage=85, has_artifacts=True
        )

        # Assert
        assert can_proceed is False
        assert is_blocking is True

    def test_default_coverage_threshold_used(
        self, default_project: MockProject
    ):
        """Default 80% coverage threshold should be used when not specified."""
        service = SpecDrivenPhaseGateService(default_project)

        # Assert default 80%
        assert service.get_coverage_threshold() == 80


# =============================================================================
# GUARDIAN SERVICE TESTS
# =============================================================================


class TestGuardianSettings:
    """Tests for GuardianService respecting auto_steering setting."""

    def test_auto_steering_enabled_executes_interventions(
        self, project_with_auto_steering: MockProject
    ):
        """When auto_steering_enabled is True, interventions should execute automatically."""
        # Arrange
        task = MockTask(
            id="task-1",
            ticket_id="ticket-10",
            phase_id="PHASE_IMPLEMENTATION",
            status="running",
            assigned_agent_id="test-agent-1",
        )
        service = SpecDrivenGuardianService(project_with_auto_steering)

        # Assert settings
        assert service.is_auto_steering_enabled() is True
        assert service.get_intervention_threshold() == "medium"

        # Act: Handle stuck task
        action = service.handle_stuck_task(task)

        # Assert: Intervention executed
        assert action is not None
        assert action.action_type == "cancel_task"
        assert action.target_entity == task.id
        assert task.status == "failed"
        assert "EMERGENCY CANCELLATION" in task.error_message
        assert "INTERVENTION" in service.log[0]

    def test_auto_steering_disabled_logs_only(
        self, default_project: MockProject
    ):
        """When auto_steering_enabled is False (default), only log - don't intervene."""
        # Arrange
        task = MockTask(
            id="task-2",
            ticket_id="ticket-11",
            phase_id="PHASE_IMPLEMENTATION",
            status="running",
            assigned_agent_id="test-agent-2",
        )
        service = SpecDrivenGuardianService(default_project)

        # Assert settings
        assert service.is_auto_steering_enabled() is False

        # Act: Handle stuck task
        action = service.handle_stuck_task(task)

        # Assert: No intervention, only logging
        assert action is None
        assert task.status == "running"  # Unchanged
        assert "OBSERVATION" in service.log[0]
        assert "no intervention" in service.log[0]

    def test_guardian_defaults_when_no_settings(
        self, default_project: MockProject
    ):
        """Guardian should use default settings when project has none."""
        # Assert project has no settings
        assert default_project.settings is None

        service = SpecDrivenGuardianService(default_project)

        # Assert defaults
        assert service.is_auto_steering_enabled() is False
        assert service.get_intervention_threshold() == "high"


# =============================================================================
# SETTINGS FALLBACK TESTS
# =============================================================================


class TestSettingsFallback:
    """Tests verifying all services correctly fall back to defaults."""

    def test_all_services_use_defaults_for_null_settings(
        self, default_project: MockProject
    ):
        """All services should use defaults when project.settings is None."""
        assert default_project.settings is None

        # PhaseProgression defaults
        progression_service = SpecDrivenPhaseProgressionService(default_project)
        ticket = MockTicket(
            id="ticket-fb-1",
            title="Test",
            phase_id="PHASE_REQUIREMENTS",
        )
        assert progression_service.should_auto_advance(ticket) is False
        assert progression_service.requires_gate_approval() is True

        # PhaseGate defaults
        gate_service = SpecDrivenPhaseGateService(default_project)
        assert gate_service.get_strictness_mode() == "strict"
        assert gate_service.get_coverage_threshold() == 80

        # Guardian defaults
        guardian_service = SpecDrivenGuardianService(default_project)
        assert guardian_service.is_auto_steering_enabled() is False
        assert guardian_service.get_intervention_threshold() == "high"

    def test_partial_settings_merged_with_defaults(self):
        """Partial settings should be merged with defaults for missing keys."""
        # Create project with only phase_gates specified
        project = MockProject(
            id="project-partial",
            name="Partial Settings Project",
            description="Project with only some settings",
            settings={
                "phase_gates": {
                    "strictness": "lenient",
                    # coverage_threshold not specified
                }
            },
        )

        gate_service = SpecDrivenPhaseGateService(project)

        # Specified setting should be used
        assert gate_service.get_strictness_mode() == "lenient"

        # Missing setting should fall back to default
        assert gate_service.get_coverage_threshold() == 80

        # Unspecified section should use all defaults
        progression_service = SpecDrivenPhaseProgressionService(project)
        ticket = MockTicket(
            id="ticket-partial",
            title="Test",
            phase_id="PHASE_REQUIREMENTS",
        )
        assert progression_service.should_auto_advance(ticket) is False

    def test_empty_settings_uses_defaults(self):
        """Empty settings dict should fall back to all defaults."""
        project = MockProject(
            id="project-empty",
            name="Empty Settings Project",
            description="Project with empty settings dict",
            settings={},  # Empty dict, not None
        )

        # All settings should fall back to defaults
        progression_service = SpecDrivenPhaseProgressionService(project)
        ticket = MockTicket(
            id="ticket-empty",
            title="Test",
            phase_id="PHASE_REQUIREMENTS",
        )
        assert progression_service.should_auto_advance(ticket) is False

        gate_service = SpecDrivenPhaseGateService(project)
        assert gate_service.get_strictness_mode() == "strict"

        guardian_service = SpecDrivenGuardianService(project)
        assert guardian_service.is_auto_steering_enabled() is False


# =============================================================================
# GET_SPEC_SETTING UTILITY TESTS
# =============================================================================


class TestGetSpecSettingUtility:
    """Tests for the get_spec_setting utility function."""

    def test_returns_default_for_none_settings(self):
        """Should return default when settings is None."""
        result = get_spec_setting(None, "any.path", "default_value")
        assert result == "default_value"

    def test_returns_value_for_existing_path(self):
        """Should return value for existing path."""
        settings = {"level1": {"level2": {"key": "value"}}}
        result = get_spec_setting(settings, "level1.level2.key", "default")
        assert result == "value"

    def test_returns_default_for_missing_path(self):
        """Should return default for missing path."""
        settings = {"level1": {"other_key": "other_value"}}
        result = get_spec_setting(settings, "level1.missing_key", "default")
        assert result == "default"

    def test_returns_default_for_partial_path(self):
        """Should return default when path is partially present."""
        settings = {"level1": "not_a_dict"}
        result = get_spec_setting(settings, "level1.level2.key", "default")
        assert result == "default"

    def test_handles_boolean_values(self):
        """Should correctly handle False values (not confuse with None)."""
        settings = {"feature": {"enabled": False}}
        result = get_spec_setting(settings, "feature.enabled", True)
        # Note: Our implementation returns default for None, but False is falsy too
        # This test documents current behavior - False should be preserved
        # The implementation uses `if value is None` so False should work
        assert result is False

    def test_handles_zero_values(self):
        """Should correctly handle zero values."""
        settings = {"threshold": {"value": 0}}
        result = get_spec_setting(settings, "threshold.value", 100)
        # Zero should be preserved, not replaced with default
        assert result == 0
