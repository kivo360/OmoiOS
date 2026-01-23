"""Unit tests for PhaseGateService settings integration."""

from unittest.mock import MagicMock, patch

import pytest

from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.spec_driven_settings import (
    GateEnforcementStrictness,
    SpecDrivenSettings,
    SpecDrivenSettingsService,
)


@pytest.mark.unit
class TestPhaseGateServiceSettingsIntegration:
    """Tests for PhaseGateService settings integration."""

    def test_init_without_settings_service(self):
        """Should initialize without settings service."""
        mock_db = MagicMock()
        service = PhaseGateService(mock_db)

        assert service.db == mock_db
        assert service.settings_service is None

    def test_init_with_settings_service(self):
        """Should initialize with settings service."""
        mock_db = MagicMock()
        mock_settings_service = MagicMock(spec=SpecDrivenSettingsService)
        service = PhaseGateService(mock_db, settings_service=mock_settings_service)

        assert service.db == mock_db
        assert service.settings_service == mock_settings_service

    def test_get_settings_for_ticket_no_service(self):
        """Should return default settings when no service configured."""
        mock_db = MagicMock()
        service = PhaseGateService(mock_db)

        settings = service._get_settings_for_ticket("ticket-123")

        assert settings.gate_enforcement_strictness == GateEnforcementStrictness.STRICT
        assert settings.min_test_coverage == 80

    def test_get_settings_for_ticket_with_service(self):
        """Should delegate to settings service when configured."""
        mock_db = MagicMock()
        mock_settings_service = MagicMock(spec=SpecDrivenSettingsService)
        custom_settings = SpecDrivenSettings(
            gate_enforcement_strictness=GateEnforcementStrictness.LENIENT,
            min_test_coverage=70,
        )
        mock_settings_service.get_settings_for_ticket.return_value = custom_settings

        service = PhaseGateService(mock_db, settings_service=mock_settings_service)
        settings = service._get_settings_for_ticket("ticket-123")

        mock_settings_service.get_settings_for_ticket.assert_called_once_with("ticket-123")
        assert settings == custom_settings


@pytest.mark.unit
class TestPhaseGateServiceStrictnessBehaviors:
    """Tests for strictness behaviors in validate_gate."""

    def _create_mock_service(self, strictness: GateEnforcementStrictness, min_coverage: int = 80):
        """Create a PhaseGateService with mocked dependencies."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        # Mock settings service
        mock_settings_service = MagicMock(spec=SpecDrivenSettingsService)
        mock_settings_service.get_settings_for_ticket.return_value = SpecDrivenSettings(
            gate_enforcement_strictness=strictness,
            min_test_coverage=min_coverage,
        )

        service = PhaseGateService(mock_db, settings_service=mock_settings_service)

        # Mock internal methods to simulate validation scenarios
        return service, mock_db, mock_session

    @patch.object(PhaseGateService, "collect_artifacts", return_value=[])
    @patch.object(PhaseGateService, "check_gate_requirements")
    @patch.object(PhaseGateService, "_evaluate_validation_criteria")
    def test_strict_mode_blocks_on_failure(
        self, mock_eval_criteria, mock_check_requirements, mock_collect
    ):
        """Strict mode should block transition when validation fails."""
        service, mock_db, mock_session = self._create_mock_service(
            GateEnforcementStrictness.STRICT
        )

        # Simulate requirements met but criteria failure
        mock_check_requirements.return_value = {
            "requirements_met": True,
            "missing_artifacts": [],
            "validation_status": "ready",
        }
        mock_eval_criteria.return_value = (False, ["Test coverage 50% below 80%"])

        # Mock the result object
        mock_result = MagicMock()
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.refresh.return_value = None
        mock_session.expunge.return_value = None

        result = service.validate_gate("ticket-123", "PHASE_IMPLEMENTATION")

        # In strict mode with failure, should get "failed" status
        # The actual result is created in the session, let's check what was passed
        add_call = mock_session.add.call_args
        created_result = add_call[0][0]
        assert created_result.gate_status == "failed"
        assert "Test coverage 50% below 80%" in (created_result.blocking_reasons or [])

    @patch.object(PhaseGateService, "collect_artifacts", return_value=[])
    @patch.object(PhaseGateService, "check_gate_requirements")
    @patch.object(PhaseGateService, "_evaluate_validation_criteria")
    def test_lenient_mode_warns_but_passes(
        self, mock_eval_criteria, mock_check_requirements, mock_collect
    ):
        """Lenient mode should warn but allow transition on validation failure."""
        service, mock_db, mock_session = self._create_mock_service(
            GateEnforcementStrictness.LENIENT
        )

        # Simulate requirements met but criteria failure
        mock_check_requirements.return_value = {
            "requirements_met": True,
            "missing_artifacts": [],
            "validation_status": "ready",
        }
        mock_eval_criteria.return_value = (False, ["Test coverage 50% below 80%"])

        result = service.validate_gate("ticket-123", "PHASE_IMPLEMENTATION")

        add_call = mock_session.add.call_args
        created_result = add_call[0][0]

        # In lenient mode, should get "passed" status even with validation issues
        assert created_result.gate_status == "passed"
        # Warnings should be in validation_result, not blocking_reasons
        assert created_result.blocking_reasons is None or created_result.blocking_reasons == []
        assert "warnings" in created_result.validation_result
        assert "Test coverage 50% below 80%" in created_result.validation_result["warnings"]

    @patch.object(PhaseGateService, "collect_artifacts", return_value=[])
    @patch.object(PhaseGateService, "check_gate_requirements")
    @patch.object(PhaseGateService, "_evaluate_validation_criteria")
    def test_bypass_mode_logs_and_passes(
        self, mock_eval_criteria, mock_check_requirements, mock_collect
    ):
        """Bypass mode should log validation result but always return success."""
        service, mock_db, mock_session = self._create_mock_service(
            GateEnforcementStrictness.BYPASS
        )

        # Simulate requirements met but criteria failure
        mock_check_requirements.return_value = {
            "requirements_met": True,
            "missing_artifacts": [],
            "validation_status": "ready",
        }
        mock_eval_criteria.return_value = (False, ["Test coverage 50% below 80%"])

        result = service.validate_gate("ticket-123", "PHASE_IMPLEMENTATION")

        add_call = mock_session.add.call_args
        created_result = add_call[0][0]

        # In bypass mode, should always get "passed" status
        assert created_result.gate_status == "passed"
        # Issues should be stored as warnings, not blocking reasons
        assert created_result.blocking_reasons is None or created_result.blocking_reasons == []
        assert "warnings" in created_result.validation_result
        assert "Test coverage 50% below 80%" in created_result.validation_result["warnings"]

    @patch.object(PhaseGateService, "collect_artifacts", return_value=[])
    @patch.object(PhaseGateService, "check_gate_requirements")
    @patch.object(PhaseGateService, "_evaluate_validation_criteria")
    def test_strictness_stored_in_result(
        self, mock_eval_criteria, mock_check_requirements, mock_collect
    ):
        """Strictness level should be stored in validation result."""
        service, mock_db, mock_session = self._create_mock_service(
            GateEnforcementStrictness.LENIENT
        )

        mock_check_requirements.return_value = {
            "requirements_met": True,
            "missing_artifacts": [],
            "validation_status": "ready",
        }
        mock_eval_criteria.return_value = (True, [])

        result = service.validate_gate("ticket-123", "PHASE_IMPLEMENTATION")

        add_call = mock_session.add.call_args
        created_result = add_call[0][0]

        assert created_result.validation_result["strictness"] == "lenient"


@pytest.mark.unit
class TestPhaseGateServiceConfigurableCoverage:
    """Tests for configurable min_test_coverage threshold."""

    def _create_mock_service_with_coverage(self, min_coverage: int):
        """Create a PhaseGateService with mocked dependencies and custom coverage."""
        mock_db = MagicMock()
        mock_session = MagicMock()
        mock_db.get_session.return_value.__enter__.return_value = mock_session

        mock_settings_service = MagicMock(spec=SpecDrivenSettingsService)
        mock_settings_service.get_settings_for_ticket.return_value = SpecDrivenSettings(
            gate_enforcement_strictness=GateEnforcementStrictness.STRICT,
            min_test_coverage=min_coverage,
        )

        service = PhaseGateService(mock_db, settings_service=mock_settings_service)
        return service, mock_db, mock_session

    @patch.object(PhaseGateService, "collect_artifacts", return_value=[])
    @patch.object(PhaseGateService, "check_gate_requirements")
    def test_custom_coverage_threshold_passes(self, mock_check_requirements, mock_collect):
        """Should pass when coverage meets custom threshold."""
        service, mock_db, mock_session = self._create_mock_service_with_coverage(50)

        mock_check_requirements.return_value = {
            "requirements_met": True,
            "missing_artifacts": [],
            "validation_status": "ready",
        }

        # Mock artifact with 60% coverage (above 50% threshold)
        mock_artifact = MagicMock()
        mock_artifact.artifact_type = "test_coverage"
        mock_artifact.artifact_content = {"percentage": 60}
        mock_code_changes = MagicMock()
        mock_code_changes.artifact_type = "code_changes"
        mock_code_changes.artifact_content = {"has_tests": True}

        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [mock_artifact, mock_code_changes]
        mock_session.query.return_value = query_mock
        mock_session.expunge.return_value = None

        result = service.validate_gate("ticket-123", "PHASE_IMPLEMENTATION")

        add_call = mock_session.add.call_args
        created_result = add_call[0][0]

        # With 60% coverage and 50% threshold, should pass
        assert created_result.gate_status == "passed"
        assert created_result.validation_result["min_test_coverage"] == 50

    @patch.object(PhaseGateService, "collect_artifacts", return_value=[])
    @patch.object(PhaseGateService, "check_gate_requirements")
    def test_custom_coverage_threshold_fails(self, mock_check_requirements, mock_collect):
        """Should fail when coverage is below custom threshold."""
        service, mock_db, mock_session = self._create_mock_service_with_coverage(90)

        mock_check_requirements.return_value = {
            "requirements_met": True,
            "missing_artifacts": [],
            "validation_status": "ready",
        }

        # Mock artifact with 85% coverage (below 90% threshold)
        mock_artifact = MagicMock()
        mock_artifact.artifact_type = "test_coverage"
        mock_artifact.artifact_content = {"percentage": 85}
        mock_code_changes = MagicMock()
        mock_code_changes.artifact_type = "code_changes"
        mock_code_changes.artifact_content = {"has_tests": True}

        query_mock = MagicMock()
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = [mock_artifact, mock_code_changes]
        mock_session.query.return_value = query_mock
        mock_session.expunge.return_value = None

        result = service.validate_gate("ticket-123", "PHASE_IMPLEMENTATION")

        add_call = mock_session.add.call_args
        created_result = add_call[0][0]

        # With 85% coverage and 90% threshold, should fail
        assert created_result.gate_status == "failed"
        assert any("85%" in r and "90%" in r for r in (created_result.blocking_reasons or []))

    @patch.object(PhaseGateService, "collect_artifacts", return_value=[])
    @patch.object(PhaseGateService, "check_gate_requirements")
    def test_coverage_threshold_stored_in_result(self, mock_check_requirements, mock_collect):
        """Custom coverage threshold should be stored in validation result."""
        service, mock_db, mock_session = self._create_mock_service_with_coverage(75)

        mock_check_requirements.return_value = {
            "requirements_met": True,
            "missing_artifacts": [],
            "validation_status": "not_configured",
        }

        result = service.validate_gate("ticket-123", "PHASE_UNKNOWN")

        add_call = mock_session.add.call_args
        created_result = add_call[0][0]

        assert created_result.validation_result["min_test_coverage"] == 75
