"""Integration tests for SpecAcceptanceValidator.

Tests the validation of Tasks against their Spec acceptance criteria:
1. CriterionResult and ValidationResult data classes
2. validate_task() with various scenarios
3. LLM-based criterion validation (mocked)
4. Event publishing for validation completions
5. get_spec_criteria_status() for spec progress tracking

These tests verify the SpecAcceptanceValidator integrates correctly
with the spec-driven development workflow.
"""

import pytest
from dataclasses import asdict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4


# =============================================================================
# Test: Data Classes
# =============================================================================


class TestCriterionResult:
    """Test CriterionResult dataclass."""

    def test_criterion_result_initialization(self):
        """Test CriterionResult initializes with all fields."""
        from omoi_os.services.spec_acceptance_validator import CriterionResult

        result = CriterionResult(
            criterion_id="criterion-123",
            criterion_text="API should return 200 OK",
            met=True,
            confidence=0.95,
            evidence="Test passed with 200 status code",
            reasoning="Response status matched expected value",
        )

        assert result.criterion_id == "criterion-123"
        assert result.criterion_text == "API should return 200 OK"
        assert result.met is True
        assert result.confidence == 0.95
        assert result.evidence == "Test passed with 200 status code"
        assert result.reasoning == "Response status matched expected value"

    def test_criterion_result_to_dict(self):
        """Test CriterionResult converts to dict correctly."""
        from omoi_os.services.spec_acceptance_validator import CriterionResult

        result = CriterionResult(
            criterion_id="criterion-456",
            criterion_text="Database records are created",
            met=False,
            confidence=0.7,
            evidence="No records found in database",
            reasoning="Expected records were not present",
        )

        result_dict = asdict(result)

        assert result_dict["criterion_id"] == "criterion-456"
        assert result_dict["met"] is False
        assert result_dict["confidence"] == 0.7


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_validation_result_initialization(self):
        """Test ValidationResult initializes with defaults."""
        from omoi_os.services.spec_acceptance_validator import ValidationResult

        result = ValidationResult(task_id="task-123", spec_task_id=None)

        assert result.task_id == "task-123"
        assert result.spec_task_id is None
        assert result.criteria_results == []
        assert result.all_criteria_met is False
        assert result.total_criteria == 0
        assert result.criteria_met_count == 0
        assert result.error is None

    def test_validation_result_completion_percentage_empty(self):
        """Test completion percentage with no criteria returns 100%."""
        from omoi_os.services.spec_acceptance_validator import ValidationResult

        result = ValidationResult(
            task_id="task-123",
            spec_task_id="spec-task-456",
            total_criteria=0,
            criteria_met_count=0,
        )

        assert result.completion_percentage == 100.0

    def test_validation_result_completion_percentage_partial(self):
        """Test completion percentage with partial criteria met."""
        from omoi_os.services.spec_acceptance_validator import ValidationResult

        result = ValidationResult(
            task_id="task-123",
            spec_task_id="spec-task-456",
            total_criteria=4,
            criteria_met_count=3,
        )

        assert result.completion_percentage == 75.0

    def test_validation_result_completion_percentage_full(self):
        """Test completion percentage with all criteria met."""
        from omoi_os.services.spec_acceptance_validator import ValidationResult

        result = ValidationResult(
            task_id="task-123",
            spec_task_id="spec-task-456",
            total_criteria=5,
            criteria_met_count=5,
            all_criteria_met=True,
        )

        assert result.completion_percentage == 100.0
        assert result.all_criteria_met is True


# =============================================================================
# Test: Validate Task - Task Not Found
# =============================================================================


class TestValidateTaskNotFound:
    """Test validate_task when task doesn't exist."""

    @pytest.mark.asyncio
    async def test_validate_task_not_found(self):
        """Test graceful handling when task not found."""
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        result = await validator.validate_task(task_id="nonexistent-task")

        assert result.task_id == "nonexistent-task"
        assert result.error is not None
        assert "not found" in result.error.lower()


# =============================================================================
# Test: Validate Task - Non-Spec Task
# =============================================================================


class TestValidateTaskNonSpec:
    """Test validate_task for tasks not linked to specs."""

    @pytest.mark.asyncio
    async def test_validate_task_no_result(self):
        """Test task without result data passes by default."""
        from omoi_os.models.task import Task
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.result = None

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        result = await validator.validate_task(task_id="task-123")

        assert result.error is not None
        assert "no result data" in result.error.lower()

    @pytest.mark.asyncio
    async def test_validate_task_no_spec_task_id(self):
        """Test task without spec_task_id auto-passes."""
        from omoi_os.models.task import Task
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.result = {"other_data": "value"}  # No spec_task_id

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_task
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        result = await validator.validate_task(task_id="task-123")

        # Non-spec tasks pass by default
        assert result.all_criteria_met is True
        assert result.error is None


# =============================================================================
# Test: Validate Task - SpecTask Not Found
# =============================================================================


class TestValidateTaskSpecTaskNotFound:
    """Test validate_task when spec_task_id points to missing SpecTask."""

    @pytest.mark.asyncio
    async def test_validate_task_spec_task_not_found(self):
        """Test handling when SpecTask doesn't exist."""
        from omoi_os.models.task import Task
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.result = {"spec_task_id": "missing-spec-task"}

        mock_db = MagicMock()
        mock_session = AsyncMock()

        # First call returns task, second returns None for SpecTask
        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = mock_task
        spec_task_result = MagicMock()
        spec_task_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(side_effect=[task_result, spec_task_result])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        result = await validator.validate_task(task_id="task-123")

        assert result.spec_task_id == "missing-spec-task"
        assert result.error is not None
        assert "spect" in result.error.lower() or "not found" in result.error.lower()


# =============================================================================
# Test: Validate Task - No Acceptance Criteria
# =============================================================================


class TestValidateTaskNoCriteria:
    """Test validate_task when spec has no acceptance criteria."""

    @pytest.mark.asyncio
    async def test_validate_task_no_criteria_auto_passes(self):
        """Test spec with no criteria auto-passes validation."""
        from omoi_os.models.task import Task
        from omoi_os.models.spec import Spec, SpecTask, SpecRequirement
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        # Create mock task
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.result = {"spec_task_id": "spec-task-456"}

        # Create mock spec task
        mock_spec_task = MagicMock(spec=SpecTask)
        mock_spec_task.id = "spec-task-456"
        mock_spec_task.spec_id = "spec-789"
        mock_spec_task.spec = MagicMock()

        # Create mock spec with empty requirements
        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-789"
        mock_spec.requirements = []  # No requirements = no criteria

        mock_db = MagicMock()
        mock_session = AsyncMock()

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = mock_task
        spec_task_result = MagicMock()
        spec_task_result.scalar_one_or_none.return_value = mock_spec_task
        spec_result = MagicMock()
        spec_result.scalar_one_or_none.return_value = mock_spec

        mock_session.execute = AsyncMock(
            side_effect=[task_result, spec_task_result, spec_result]
        )
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        result = await validator.validate_task(task_id="task-123")

        assert result.all_criteria_met is True
        assert result.total_criteria == 0


# =============================================================================
# Test: Validate Task - With Criteria (Mocked LLM)
# =============================================================================


class TestValidateTaskWithCriteria:
    """Test validate_task with mocked LLM validation."""

    @pytest.fixture
    def mock_spec_with_criteria(self):
        """Create a mock spec with acceptance criteria."""
        from omoi_os.models.spec import (
            Spec,
            SpecTask,
            SpecRequirement,
            SpecAcceptanceCriterion,
        )

        # Create criteria
        criterion1 = MagicMock(spec=SpecAcceptanceCriterion)
        criterion1.id = "criterion-1"
        criterion1.text = "API returns 200 status code"
        criterion1.completed = False

        criterion2 = MagicMock(spec=SpecAcceptanceCriterion)
        criterion2.id = "criterion-2"
        criterion2.text = "Response body contains expected data"
        criterion2.completed = False

        # Create requirement with criteria
        requirement = MagicMock(spec=SpecRequirement)
        requirement.id = "req-1"
        requirement.title = "API Endpoint"
        requirement.criteria = [criterion1, criterion2]

        # Create spec
        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.title = "Test Feature"
        mock_spec.description = "Test feature implementation"
        mock_spec.requirements = [requirement]

        # Create spec task
        mock_spec_task = MagicMock(spec=SpecTask)
        mock_spec_task.id = "spec-task-456"
        mock_spec_task.spec_id = "spec-123"
        mock_spec_task.title = "Implement API"
        mock_spec_task.description = "Create API endpoint"
        mock_spec_task.phase = "Implementation"
        mock_spec_task.spec = mock_spec

        return mock_spec, mock_spec_task, [criterion1, criterion2]

    @pytest.mark.asyncio
    async def test_validate_task_all_criteria_met(self, mock_spec_with_criteria):
        """Test validation when all criteria are met."""
        from omoi_os.models.task import Task
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator
        from pydantic import BaseModel

        mock_spec, mock_spec_task, criteria = mock_spec_with_criteria

        # Create mock task
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.status = "completed"
        mock_task.description = "Implement the API endpoint"
        mock_task.result = {
            "spec_task_id": "spec-task-456",
            "implementation_result": {"status": "success"},
        }

        # Mock LLM response - all criteria met
        class MockLLMResponse(BaseModel):
            met: bool = True
            confidence: float = 0.95
            evidence: str = "Implementation matches criterion"
            reasoning: str = "The code satisfies the requirement"

        mock_llm = MagicMock()
        mock_llm.structured_output = AsyncMock(return_value=MockLLMResponse())

        mock_db = MagicMock()
        mock_session = AsyncMock()

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = mock_task
        spec_task_result = MagicMock()
        spec_task_result.scalar_one_or_none.return_value = mock_spec_task
        spec_result = MagicMock()
        spec_result.scalar_one_or_none.return_value = mock_spec

        mock_session.execute = AsyncMock(
            side_effect=[task_result, spec_task_result, spec_result]
        )
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db, llm_service=mock_llm)
        result = await validator.validate_task(task_id="task-123")

        assert result.all_criteria_met is True
        assert result.total_criteria == 2
        assert result.criteria_met_count == 2
        assert result.completion_percentage == 100.0
        assert len(result.criteria_results) == 2

    @pytest.mark.asyncio
    async def test_validate_task_partial_criteria_met(self, mock_spec_with_criteria):
        """Test validation when some criteria are not met."""
        from omoi_os.models.task import Task
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator
        from pydantic import BaseModel

        mock_spec, mock_spec_task, criteria = mock_spec_with_criteria

        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.status = "completed"
        mock_task.description = "Implement the API endpoint"
        mock_task.result = {"spec_task_id": "spec-task-456"}

        # Mock LLM response - first met, second not met
        call_count = [0]

        class MockLLMResponse(BaseModel):
            met: bool
            confidence: float
            evidence: str
            reasoning: str

        async def mock_structured_output(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return MockLLMResponse(
                    met=True,
                    confidence=0.9,
                    evidence="First criterion met",
                    reasoning="Implementation correct",
                )
            else:
                return MockLLMResponse(
                    met=False,
                    confidence=0.8,
                    evidence="Second criterion not met",
                    reasoning="Missing expected data",
                )

        mock_llm = MagicMock()
        mock_llm.structured_output = AsyncMock(side_effect=mock_structured_output)

        mock_db = MagicMock()
        mock_session = AsyncMock()

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = mock_task
        spec_task_result = MagicMock()
        spec_task_result.scalar_one_or_none.return_value = mock_spec_task
        spec_result = MagicMock()
        spec_result.scalar_one_or_none.return_value = mock_spec

        mock_session.execute = AsyncMock(
            side_effect=[task_result, spec_task_result, spec_result]
        )
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db, llm_service=mock_llm)
        result = await validator.validate_task(task_id="task-123")

        assert result.all_criteria_met is False
        assert result.total_criteria == 2
        assert result.criteria_met_count == 1
        assert result.completion_percentage == 50.0


# =============================================================================
# Test: Event Publishing
# =============================================================================


class TestEventPublishing:
    """Test event publishing during validation."""

    @pytest.mark.asyncio
    async def test_publishes_validation_event(self):
        """Test SPEC_CRITERIA_VALIDATED event is published."""
        from omoi_os.models.task import Task
        from omoi_os.models.spec import (
            Spec,
            SpecTask,
            SpecRequirement,
            SpecAcceptanceCriterion,
        )
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator
        from omoi_os.services.event_bus import EventBusService
        from pydantic import BaseModel

        # Create criterion
        criterion = MagicMock(spec=SpecAcceptanceCriterion)
        criterion.id = "criterion-1"
        criterion.text = "Test criterion"
        criterion.completed = False

        # Create requirement
        requirement = MagicMock(spec=SpecRequirement)
        requirement.id = "req-1"
        requirement.criteria = [criterion]

        # Create spec
        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.title = "Test"
        mock_spec.description = "Test"
        mock_spec.requirements = [requirement]

        # Create spec task
        mock_spec_task = MagicMock(spec=SpecTask)
        mock_spec_task.id = "spec-task-456"
        mock_spec_task.spec_id = "spec-123"
        mock_spec_task.title = "Test"
        mock_spec_task.description = "Test"
        mock_spec_task.phase = "Implementation"
        mock_spec_task.spec = mock_spec

        # Create task
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.status = "completed"
        mock_task.description = "Test"
        mock_task.result = {"spec_task_id": "spec-task-456"}

        # Mock LLM
        class MockLLMResponse(BaseModel):
            met: bool = True
            confidence: float = 0.9
            evidence: str = "Evidence"
            reasoning: str = "Reasoning"

        mock_llm = MagicMock()
        mock_llm.structured_output = AsyncMock(return_value=MockLLMResponse())

        # Mock event bus
        mock_event_bus = MagicMock(spec=EventBusService)
        mock_event_bus.publish = MagicMock()

        # Mock database
        mock_db = MagicMock()
        mock_session = AsyncMock()

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = mock_task
        spec_task_result = MagicMock()
        spec_task_result.scalar_one_or_none.return_value = mock_spec_task
        spec_result = MagicMock()
        spec_result.scalar_one_or_none.return_value = mock_spec

        mock_session.execute = AsyncMock(
            side_effect=[task_result, spec_task_result, spec_result]
        )
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(
            db=mock_db,
            llm_service=mock_llm,
            event_bus=mock_event_bus,
        )
        result = await validator.validate_task(task_id="task-123")

        # Verify event was published
        mock_event_bus.publish.assert_called_once()
        event = mock_event_bus.publish.call_args[0][0]
        assert event.event_type == "SPEC_CRITERIA_VALIDATED"
        assert event.entity_type == "task"
        assert event.entity_id == "task-123"
        assert event.payload["spec_task_id"] == "spec-task-456"
        assert event.payload["all_criteria_met"] is True


# =============================================================================
# Test: Get Spec Criteria Status
# =============================================================================


class TestGetSpecCriteriaStatus:
    """Test get_spec_criteria_status method."""

    @pytest.mark.asyncio
    async def test_get_status_returns_correct_counts(self):
        """Test status returns correct completion counts."""
        from omoi_os.models.spec import Spec, SpecRequirement, SpecAcceptanceCriterion
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        # Create criteria with mixed completion status
        criterion1 = MagicMock(spec=SpecAcceptanceCriterion)
        criterion1.id = "c1"
        criterion1.text = "Criterion 1"
        criterion1.completed = True

        criterion2 = MagicMock(spec=SpecAcceptanceCriterion)
        criterion2.id = "c2"
        criterion2.text = "Criterion 2"
        criterion2.completed = True

        criterion3 = MagicMock(spec=SpecAcceptanceCriterion)
        criterion3.id = "c3"
        criterion3.text = "Criterion 3"
        criterion3.completed = False

        # Create requirements
        req1 = MagicMock(spec=SpecRequirement)
        req1.id = "req-1"
        req1.title = "Requirement 1"
        req1.criteria = [criterion1, criterion2]

        req2 = MagicMock(spec=SpecRequirement)
        req2.id = "req-2"
        req2.title = "Requirement 2"
        req2.criteria = [criterion3]

        # Create spec
        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.requirements = [req1, req2]

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_spec
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        status = await validator.get_spec_criteria_status(spec_id="spec-123")

        assert status["spec_id"] == "spec-123"
        assert status["total_criteria"] == 3
        assert status["completed_criteria"] == 2
        assert status["completion_percentage"] == pytest.approx(66.67, rel=0.01)
        assert status["all_complete"] is False

    @pytest.mark.asyncio
    async def test_get_status_all_complete(self):
        """Test status when all criteria are complete."""
        from omoi_os.models.spec import Spec, SpecRequirement, SpecAcceptanceCriterion
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        criterion = MagicMock(spec=SpecAcceptanceCriterion)
        criterion.id = "c1"
        criterion.text = "Criterion 1"
        criterion.completed = True

        req = MagicMock(spec=SpecRequirement)
        req.id = "req-1"
        req.title = "Requirement 1"
        req.criteria = [criterion]

        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.requirements = [req]

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_spec
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        status = await validator.get_spec_criteria_status(spec_id="spec-123")

        assert status["all_complete"] is True
        assert status["completion_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_get_status_spec_not_found(self):
        """Test status when spec not found."""
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        status = await validator.get_spec_criteria_status(spec_id="nonexistent")

        assert "error" in status
        assert "not found" in status["error"].lower()

    @pytest.mark.asyncio
    async def test_get_status_by_requirement(self):
        """Test status breakdown by requirement."""
        from omoi_os.models.spec import Spec, SpecRequirement, SpecAcceptanceCriterion
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        # Create criteria
        c1 = MagicMock(spec=SpecAcceptanceCriterion)
        c1.id = "c1"
        c1.text = "C1"
        c1.completed = True

        c2 = MagicMock(spec=SpecAcceptanceCriterion)
        c2.id = "c2"
        c2.text = "C2"
        c2.completed = False

        # Create requirement
        req = MagicMock(spec=SpecRequirement)
        req.id = "req-1"
        req.title = "API Requirement"
        req.criteria = [c1, c2]

        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.requirements = [req]

        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_spec
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db)
        status = await validator.get_spec_criteria_status(spec_id="spec-123")

        assert "by_requirement" in status
        req_status = status["by_requirement"]["req-1"]
        assert req_status["requirement_title"] == "API Requirement"
        assert req_status["total"] == 2
        assert req_status["completed"] == 1
        assert len(req_status["criteria"]) == 2


# =============================================================================
# Test: LLM Failure Handling
# =============================================================================


class TestLLMFailureHandling:
    """Test handling of LLM failures during validation."""

    @pytest.mark.asyncio
    async def test_llm_failure_marks_criterion_unmet(self):
        """Test LLM failure results in criterion marked as unmet."""
        from omoi_os.models.task import Task
        from omoi_os.models.spec import (
            Spec,
            SpecTask,
            SpecRequirement,
            SpecAcceptanceCriterion,
        )
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        # Create criterion
        criterion = MagicMock(spec=SpecAcceptanceCriterion)
        criterion.id = "criterion-1"
        criterion.text = "Test criterion"
        criterion.completed = False

        # Create requirement
        requirement = MagicMock(spec=SpecRequirement)
        requirement.id = "req-1"
        requirement.criteria = [criterion]

        # Create spec
        mock_spec = MagicMock(spec=Spec)
        mock_spec.id = "spec-123"
        mock_spec.title = "Test"
        mock_spec.description = "Test"
        mock_spec.requirements = [requirement]

        # Create spec task
        mock_spec_task = MagicMock(spec=SpecTask)
        mock_spec_task.id = "spec-task-456"
        mock_spec_task.spec_id = "spec-123"
        mock_spec_task.title = "Test"
        mock_spec_task.description = "Test"
        mock_spec_task.phase = "Implementation"
        mock_spec_task.spec = mock_spec

        # Create task
        mock_task = MagicMock(spec=Task)
        mock_task.id = "task-123"
        mock_task.status = "completed"
        mock_task.description = "Test"
        mock_task.result = {"spec_task_id": "spec-task-456"}

        # Mock LLM that fails
        mock_llm = MagicMock()
        mock_llm.structured_output = AsyncMock(
            side_effect=Exception("LLM API Error")
        )

        mock_db = MagicMock()
        mock_session = AsyncMock()

        task_result = MagicMock()
        task_result.scalar_one_or_none.return_value = mock_task
        spec_task_result = MagicMock()
        spec_task_result.scalar_one_or_none.return_value = mock_spec_task
        spec_result = MagicMock()
        spec_result.scalar_one_or_none.return_value = mock_spec

        mock_session.execute = AsyncMock(
            side_effect=[task_result, spec_task_result, spec_result]
        )
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_db.get_async_session = MagicMock(return_value=mock_session)

        validator = SpecAcceptanceValidator(db=mock_db, llm_service=mock_llm)
        result = await validator.validate_task(task_id="task-123")

        # Criterion should be marked as unmet on LLM failure
        assert result.all_criteria_met is False
        assert result.criteria_met_count == 0
        assert len(result.criteria_results) == 1
        assert result.criteria_results[0].met is False
        assert result.criteria_results[0].confidence == 0.0
        assert "failed" in result.criteria_results[0].reasoning.lower()


# =============================================================================
# Test: Implementation Context Building
# =============================================================================


class TestImplementationContextBuilding:
    """Test the _build_implementation_context method."""

    def test_builds_context_with_all_data(self):
        """Test context building includes all relevant data."""
        from omoi_os.models.task import Task
        from omoi_os.models.spec import Spec, SpecTask
        from omoi_os.services.spec_acceptance_validator import SpecAcceptanceValidator

        mock_task = MagicMock(spec=Task)
        mock_task.status = "completed"
        mock_task.description = "Task description"
        mock_task.result = {
            "implementation_result": {
                "status": "success",
                "files_changed": 3,
            }
        }

        mock_spec_task = MagicMock(spec=SpecTask)
        mock_spec_task.title = "Implement feature"
        mock_spec_task.description = "Feature implementation"
        mock_spec_task.phase = "Implementation"

        mock_spec = MagicMock(spec=Spec)
        mock_spec.title = "Feature Spec"
        mock_spec.description = "Spec description"

        evidence = {"pr_url": "https://github.com/pr/123"}

        mock_db = MagicMock()
        validator = SpecAcceptanceValidator(db=mock_db)

        context = validator._build_implementation_context(
            task=mock_task,
            spec_task=mock_spec_task,
            spec=mock_spec,
            evidence=evidence,
        )

        # Verify context includes key information
        assert "Feature Spec" in context
        assert "Spec description" in context
        assert "Implement feature" in context
        assert "Implementation" in context
        assert "completed" in context
        assert "success" in context
        assert "pr_url" in context


# =============================================================================
# Test: Factory Function
# =============================================================================


class TestGetSpecAcceptanceValidator:
    """Test the factory function."""

    def test_creates_validator_with_defaults(self):
        """Test factory creates validator with default services."""
        from omoi_os.services.spec_acceptance_validator import (
            get_spec_acceptance_validator,
        )

        # Patch at the source where get_db_service is imported
        with patch("omoi_os.api.dependencies.get_db_service") as mock_get_db:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            validator = get_spec_acceptance_validator()

            assert validator.db == mock_db
            mock_get_db.assert_called_once()

    def test_creates_validator_with_provided_services(self):
        """Test factory uses provided services."""
        from omoi_os.services.spec_acceptance_validator import (
            get_spec_acceptance_validator,
            SpecAcceptanceValidator,
        )

        mock_db = MagicMock()
        mock_llm = MagicMock()
        mock_event_bus = MagicMock()

        validator = get_spec_acceptance_validator(
            db=mock_db,
            llm_service=mock_llm,
            event_bus=mock_event_bus,
        )

        assert validator.db == mock_db
        assert validator.llm_service == mock_llm
        assert validator.event_bus == mock_event_bus
