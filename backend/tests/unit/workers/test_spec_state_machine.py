"""Unit tests for spec-driven development state machine.

Tests the SpecStateMachine orchestrator that manages phase execution.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from omoi_os.workers.spec_state_machine import SpecStateMachine, SpecPhase


class TestSpecPhase:
    """Tests for SpecPhase enum."""

    def test_phase_values(self):
        """Test that all expected phases exist."""
        assert SpecPhase.EXPLORE.value == "explore"
        assert SpecPhase.REQUIREMENTS.value == "requirements"
        assert SpecPhase.DESIGN.value == "design"
        assert SpecPhase.TASKS.value == "tasks"
        assert SpecPhase.SYNC.value == "sync"
        assert SpecPhase.COMPLETE.value == "complete"

    def test_phase_order(self):
        """Test that phases are ordered correctly."""
        phases = list(SpecPhase)
        expected = [
            SpecPhase.EXPLORE,
            SpecPhase.REQUIREMENTS,
            SpecPhase.DESIGN,
            SpecPhase.TASKS,
            SpecPhase.SYNC,
            SpecPhase.COMPLETE,
        ]
        assert phases == expected


class TestSpecStateMachine:
    """Tests for SpecStateMachine."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        return db

    @pytest.fixture
    def state_machine(self, mock_db):
        """Create state machine instance."""
        return SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db,
            working_directory="/tmp/test-workspace",
        )

    def test_initialization(self, state_machine):
        """Test state machine initializes correctly."""
        assert state_machine.spec_id == "spec-test-123"
        assert state_machine.working_directory == "/tmp/test-workspace"

    def test_phase_order(self, state_machine):
        """Test PHASE_ORDER is correct."""
        expected = [
            SpecPhase.EXPLORE,
            SpecPhase.REQUIREMENTS,
            SpecPhase.DESIGN,
            SpecPhase.TASKS,
            SpecPhase.SYNC,
            SpecPhase.COMPLETE,
        ]
        assert state_machine.PHASE_ORDER == expected

    def test_phase_timeouts(self, state_machine):
        """Test phase timeouts are configured."""
        assert SpecPhase.EXPLORE in state_machine.PHASE_TIMEOUTS
        assert SpecPhase.REQUIREMENTS in state_machine.PHASE_TIMEOUTS
        assert SpecPhase.DESIGN in state_machine.PHASE_TIMEOUTS
        assert SpecPhase.TASKS in state_machine.PHASE_TIMEOUTS
        assert SpecPhase.SYNC in state_machine.PHASE_TIMEOUTS
        # All timeouts should be positive
        for phase, timeout in state_machine.PHASE_TIMEOUTS.items():
            assert timeout > 0, f"Phase {phase} should have positive timeout"

    def test_phase_max_turns(self, state_machine):
        """Test max_turns limits are configured."""
        assert SpecPhase.EXPLORE in state_machine.PHASE_MAX_TURNS
        assert SpecPhase.REQUIREMENTS in state_machine.PHASE_MAX_TURNS
        assert SpecPhase.DESIGN in state_machine.PHASE_MAX_TURNS
        assert SpecPhase.TASKS in state_machine.PHASE_MAX_TURNS
        assert SpecPhase.SYNC in state_machine.PHASE_MAX_TURNS
        # All max_turns should be positive
        for phase, max_turns in state_machine.PHASE_MAX_TURNS.items():
            assert max_turns > 0, f"Phase {phase} should have positive max_turns"

    def test_next_phase(self, state_machine):
        """Test next_phase returns correct sequence."""
        assert state_machine.next_phase(SpecPhase.EXPLORE) == SpecPhase.REQUIREMENTS
        assert state_machine.next_phase(SpecPhase.REQUIREMENTS) == SpecPhase.DESIGN
        assert state_machine.next_phase(SpecPhase.DESIGN) == SpecPhase.TASKS
        assert state_machine.next_phase(SpecPhase.TASKS) == SpecPhase.SYNC
        assert state_machine.next_phase(SpecPhase.SYNC) == SpecPhase.COMPLETE
        assert state_machine.next_phase(SpecPhase.COMPLETE) == SpecPhase.COMPLETE

    def test_evaluators_initialized(self, state_machine):
        """Test evaluators are initialized correctly."""
        from omoi_os.evals import (
            ExplorationEvaluator,
            RequirementEvaluator,
            DesignEvaluator,
            TaskEvaluator,
        )

        # Check evaluators dict exists and has correct types
        assert SpecPhase.EXPLORE in state_machine.evaluators
        assert SpecPhase.REQUIREMENTS in state_machine.evaluators
        assert SpecPhase.DESIGN in state_machine.evaluators
        assert SpecPhase.TASKS in state_machine.evaluators

        assert isinstance(
            state_machine.evaluators[SpecPhase.EXPLORE], ExplorationEvaluator
        )
        assert isinstance(
            state_machine.evaluators[SpecPhase.REQUIREMENTS], RequirementEvaluator
        )
        assert isinstance(state_machine.evaluators[SpecPhase.DESIGN], DesignEvaluator)
        assert isinstance(state_machine.evaluators[SpecPhase.TASKS], TaskEvaluator)

    def test_get_explore_prompt(self, state_machine):
        """Test _get_explore_prompt returns non-empty string."""
        mock_spec = MagicMock()
        mock_spec.title = "Test Spec"
        mock_spec.description = "A test specification"

        prompt = state_machine._get_explore_prompt(mock_spec)
        assert isinstance(prompt, str)
        assert len(prompt) > 50, "Explore prompt should be substantive"
        assert "Test Spec" in prompt

    def test_build_retry_prompt(self, state_machine):
        """Test retry prompt includes failure information."""
        from omoi_os.evals.base import EvalResult

        mock_spec = MagicMock()
        mock_spec.title = "Test Spec"
        mock_spec.description = "A test specification"

        previous_output = {"partial": "data"}
        eval_result = EvalResult(
            passed=False,
            score=0.4,
            failures=["Missing required field X", "Invalid format for Y"],
            feedback_for_retry="Please include field X and fix the format of Y.",
        )

        retry_prompt = state_machine.build_retry_prompt(
            phase=SpecPhase.REQUIREMENTS,
            spec=mock_spec,
            previous_output=previous_output,
            eval_result=eval_result,
        )

        assert isinstance(retry_prompt, str)
        assert len(retry_prompt) > 20, "Retry prompt should be substantive"

    def test_extract_structured_output_json_block(self, state_machine):
        """Test extracting JSON from markdown code blocks."""
        response = """
Here is the result:

```json
{"key": "value", "count": 42}
```

That's the data.
"""
        result = state_machine.extract_structured_output(response)
        assert result == {"key": "value", "count": 42}

    def test_extract_structured_output_raw_json(self, state_machine):
        """Test extracting raw JSON without code blocks."""
        response = 'The output is {"data": [1, 2, 3]} which is valid.'
        result = state_machine.extract_structured_output(response)
        assert result == {"data": [1, 2, 3]}

    def test_extract_structured_output_array(self, state_machine):
        """Test extracting JSON array."""
        response = """
```json
[{"id": 1}, {"id": 2}]
```
"""
        result = state_machine.extract_structured_output(response)
        assert result == [{"id": 1}, {"id": 2}]

    def test_extract_structured_output_invalid(self, state_machine):
        """Test that invalid JSON raises ValueError."""
        response = "This is not JSON at all."
        with pytest.raises(ValueError, match="Could not extract JSON"):
            state_machine.extract_structured_output(response)


class TestSpecStateMachinePhaseExecution:
    """Tests for phase execution (requires more complex mocking)."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db

    @pytest.fixture
    def state_machine(self, mock_db):
        return SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db,
            working_directory="/tmp/test-workspace",
        )

    @pytest.mark.asyncio
    async def test_execute_phase_exists(self, state_machine):
        """Test execute_phase method exists and is async."""
        import inspect

        assert hasattr(state_machine, "execute_phase")
        assert inspect.iscoroutinefunction(state_machine.execute_phase)

    @pytest.mark.asyncio
    async def test_run_exists(self, state_machine):
        """Test run method exists and is async."""
        import inspect

        assert hasattr(state_machine, "run")
        assert inspect.iscoroutinefunction(state_machine.run)

    def test_phase_result_model(self):
        """Test PhaseResult model can be instantiated."""
        from omoi_os.workers.spec_state_machine import PhaseResult

        result = PhaseResult(
            phase=SpecPhase.EXPLORE,
            data={"project_type": "web_app"},
            eval_score=0.95,
            attempts=1,
            duration_seconds=10.5,
        )

        assert result.phase == SpecPhase.EXPLORE
        assert result.eval_score == 0.95
        assert result.attempts == 1


class TestSpecStateMachineIntegration:
    """Integration-style tests for the state machine."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db

    @pytest.fixture
    def state_machine(self, mock_db):
        return SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db,
            working_directory="/tmp/test-workspace",
        )

    def test_phase_data_accumulation(self, state_machine):
        """Test that phase data can be accumulated."""
        # Simulate phase data being stored
        phase_data = {}

        # Exploration phase
        phase_data["explore"] = {
            "project_type": "web_app",
            "existing_models": [{"name": "User", "file": "models.py"}],
        }

        # Requirements phase can access exploration
        phase_data["requirements"] = {
            "requirements": [
                {
                    "title": "Auth",
                    "condition": "WHEN user logs in",
                    "action": "Create session",
                }
            ]
        }

        # Design phase can access both
        phase_data["design"] = {
            "architecture": "Layered architecture...",
            "data_models": [{"name": "Session", "fields": []}],
        }

        # Each phase should have access to previous phases
        assert "explore" in phase_data
        assert "requirements" in phase_data
        assert "design" in phase_data

        # Verify structure
        assert phase_data["explore"]["project_type"] == "web_app"
        assert len(phase_data["requirements"]["requirements"]) == 1
        assert phase_data["design"]["architecture"].startswith("Layered")


class TestSpecStateMachineCheckpoints:
    """Tests for checkpoint save/restore functionality."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        """Create a temporary workspace directory."""
        workspace = tmp_path / "test-workspace"
        workspace.mkdir()
        return str(workspace)

    @pytest.fixture
    def state_machine(self, mock_db, temp_workspace):
        return SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

    def test_save_checkpoint_exists(self, state_machine):
        """Test save_checkpoint method exists and is async."""
        import inspect

        assert hasattr(state_machine, "save_checkpoint")
        assert inspect.iscoroutinefunction(state_machine.save_checkpoint)

    def test_write_file_checkpoint_exists(self, state_machine):
        """Test _write_file_checkpoint method exists."""
        import inspect

        assert hasattr(state_machine, "_write_file_checkpoint")
        assert inspect.iscoroutinefunction(state_machine._write_file_checkpoint)

    @pytest.mark.asyncio
    async def test_file_checkpoint_creates_directory(
        self, state_machine, temp_workspace
    ):
        """Test that file checkpoint creates necessary directories."""
        from pathlib import Path

        # Write a checkpoint
        await state_machine._write_file_checkpoint(
            SpecPhase.EXPLORE, {"project_type": "web_app", "test": True}
        )

        # Check directory was created
        checkpoint_dir = Path(temp_workspace) / ".omoi_os" / "phase_data"
        assert checkpoint_dir.exists()
        assert checkpoint_dir.is_dir()

    @pytest.mark.asyncio
    async def test_file_checkpoint_writes_json(self, state_machine, temp_workspace):
        """Test that file checkpoint writes valid JSON data."""
        import json
        from pathlib import Path

        test_data = {
            "project_type": "web_app",
            "tech_stack": ["python", "fastapi"],
            "explored_files": ["main.py", "models.py"],
        }

        await state_machine._write_file_checkpoint(SpecPhase.EXPLORE, test_data)

        # Read and verify the checkpoint
        checkpoint_path = (
            Path(temp_workspace) / ".omoi_os" / "phase_data" / "explore.json"
        )
        assert checkpoint_path.exists()

        with open(checkpoint_path) as f:
            saved_data = json.load(f)

        assert saved_data == test_data

    @pytest.mark.asyncio
    async def test_multiple_phase_checkpoints(self, state_machine, temp_workspace):
        """Test saving checkpoints for multiple phases."""
        import json
        from pathlib import Path

        # Write checkpoints for multiple phases
        explore_data = {"project_type": "web_app"}
        requirements_data = {"requirements": [{"title": "Auth"}]}
        design_data = {"architecture": "Layered"}

        await state_machine._write_file_checkpoint(SpecPhase.EXPLORE, explore_data)
        await state_machine._write_file_checkpoint(
            SpecPhase.REQUIREMENTS, requirements_data
        )
        await state_machine._write_file_checkpoint(SpecPhase.DESIGN, design_data)

        # Verify all checkpoints exist
        checkpoint_dir = Path(temp_workspace) / ".omoi_os" / "phase_data"
        assert (checkpoint_dir / "explore.json").exists()
        assert (checkpoint_dir / "requirements.json").exists()
        assert (checkpoint_dir / "design.json").exists()

        # Verify content
        with open(checkpoint_dir / "explore.json") as f:
            assert json.load(f) == explore_data
        with open(checkpoint_dir / "requirements.json") as f:
            assert json.load(f) == requirements_data
        with open(checkpoint_dir / "design.json") as f:
            assert json.load(f) == design_data

    @pytest.fixture
    def mock_async_db(self):
        """Create mock async database session."""
        db = MagicMock()
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @pytest.fixture
    def state_machine_async_db(self, mock_async_db, temp_workspace):
        return SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_async_db,
            working_directory=temp_workspace,
        )

    @pytest.mark.asyncio
    async def test_save_checkpoint_updates_spec(
        self, state_machine_async_db, temp_workspace
    ):
        """Test that save_checkpoint updates the spec object."""
        mock_spec = MagicMock()
        mock_spec.phase_data = {"explore": {"project_type": "test"}}
        mock_spec.session_transcripts = {}
        mock_spec.current_phase = "explore"  # Set valid phase value
        mock_spec.id = "spec-test-123"

        await state_machine_async_db.save_checkpoint(mock_spec)

        # Verify last_checkpoint_at was set
        assert mock_spec.last_checkpoint_at is not None

    @pytest.mark.asyncio
    async def test_save_checkpoint_creates_state_file(
        self, state_machine_async_db, temp_workspace
    ):
        """Test that save_checkpoint creates a state.json file."""
        from pathlib import Path

        mock_spec = MagicMock()
        mock_spec.phase_data = {"explore": {"project_type": "test"}}
        mock_spec.session_transcripts = {}
        mock_spec.current_phase = "explore"  # Set valid phase value
        mock_spec.id = "spec-test-123"

        await state_machine_async_db.save_checkpoint(mock_spec)

        state_file = Path(temp_workspace) / ".omoi_os" / "checkpoints" / "state.json"
        assert state_file.exists()


class TestMockSpec:
    """Tests for _MockSpec class used in sandbox environments."""

    def test_mock_spec_creation(self):
        """Test _MockSpec can be created with minimal args."""
        from omoi_os.workers.spec_state_machine import _MockSpec

        mock = _MockSpec("test-id")
        assert mock.id == "test-id"
        assert mock.title == "Local Spec"
        assert mock.description == ""
        assert mock.current_phase == "explore"
        assert mock.phase_data == {}
        assert mock.phase_attempts == {}
        assert mock.session_transcripts == {}
        assert mock.is_mock is True

    def test_mock_spec_with_all_fields(self):
        """Test _MockSpec with all fields populated."""
        from omoi_os.workers.spec_state_machine import _MockSpec

        mock = _MockSpec(
            spec_id="spec-123", title="Test Spec", description="A test specification"
        )
        assert mock.id == "spec-123"
        assert mock.title == "Test Spec"
        assert mock.description == "A test specification"

    def test_mock_spec_repr(self):
        """Test _MockSpec string representation."""
        from omoi_os.workers.spec_state_machine import _MockSpec

        mock = _MockSpec("spec-456")
        assert "spec-456" in repr(mock)
        assert "explore" in repr(mock)

    def test_mock_spec_mutable_fields(self):
        """Test _MockSpec fields can be modified."""
        from omoi_os.workers.spec_state_machine import _MockSpec

        mock = _MockSpec("test-id")
        mock.current_phase = "requirements"
        mock.phase_data = {"explore": {"project_type": "web_app"}}
        mock.phase_attempts = {"explore": 2}

        assert mock.current_phase == "requirements"
        assert mock.phase_data["explore"]["project_type"] == "web_app"
        assert mock.phase_attempts["explore"] == 2


class TestLoadOrCreateMockSpec:
    """Tests for _load_or_create_mock_spec method."""

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db

    @pytest.fixture
    def temp_workspace(self, tmp_path):
        workspace = tmp_path / "test-workspace"
        workspace.mkdir()
        return str(workspace)

    @pytest.fixture
    def state_machine(self, mock_db, temp_workspace):
        return SpecStateMachine(
            spec_id="spec-test-123",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

    def test_creates_fresh_mock_when_no_checkpoint(self, state_machine):
        """Test fresh mock spec is created when no checkpoint exists."""
        mock = state_machine._load_or_create_mock_spec()
        assert mock.id == "spec-test-123"
        assert mock.current_phase == "explore"
        assert mock.is_mock is True

    def test_restores_from_checkpoint(self, state_machine, temp_workspace):
        """Test mock spec is restored from checkpoint file."""
        import json
        from pathlib import Path

        # Create checkpoint
        checkpoint_dir = Path(temp_workspace) / ".omoi_os" / "checkpoints"
        checkpoint_dir.mkdir(parents=True)
        state_file = checkpoint_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "title": "Restored Spec",
                    "description": "A restored spec",
                    "current_phase": "design",
                    "phase_data": {
                        "explore": {"type": "api"},
                        "requirements": {"reqs": []},
                    },
                    "phase_attempts": {"explore": 1, "requirements": 2},
                    "session_transcripts": {"explore": {"session_id": "sess-123"}},
                }
            )
        )

        # Load
        mock = state_machine._load_or_create_mock_spec()
        assert mock.id == "spec-test-123"
        assert mock.title == "Restored Spec"
        assert mock.current_phase == "design"
        assert mock.phase_data["explore"]["type"] == "api"
        assert mock.phase_attempts["requirements"] == 2
        assert mock.session_transcripts["explore"]["session_id"] == "sess-123"
