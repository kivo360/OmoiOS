"""
Local integration tests for the spec state machine.

These tests verify the spec state machine can run in an isolated environment
without requiring a full backend setup (no database, no redis, etc).

The tests simulate what happens when the worker runs in a Daytona sandbox.
"""

import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestSpecStateMachineLocalExecution:
    """Test the spec state machine can run locally without external dependencies."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        workspace = tempfile.mkdtemp(prefix="spec_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session that mimics _MockDatabaseSession."""
        db = MagicMock()
        db._pending_operations = []  # Marker to identify as mock

        async def async_noop(*args, **kwargs):
            pass

        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.close = AsyncMock()
        db.add = MagicMock()

        # Create mock result that mimics database behavior
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)

        return db

    def test_state_machine_imports_without_database(self):
        """Test that SpecStateMachine can be imported without database deps."""
        # This should work even without pgvector installed
        from omoi_os.workers.spec_state_machine import (
            PhaseResult,
            SpecPhase,
            SpecStateMachine,
            _MockSpec,
        )

        assert SpecStateMachine is not None
        assert SpecPhase is not None
        assert PhaseResult is not None
        assert _MockSpec is not None

    def test_state_machine_creation(self, mock_db, temp_workspace):
        """Test SpecStateMachine can be instantiated."""
        from omoi_os.workers.spec_state_machine import SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test-spec-123",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        assert machine.spec_id == "test-spec-123"
        assert machine.working_directory == temp_workspace
        assert machine.max_retries == 3
        assert len(machine.evaluators) == 4

    @pytest.mark.asyncio
    async def test_load_spec_uses_mock_when_no_database(self, mock_db, temp_workspace):
        """Test load_spec returns _MockSpec when database is unavailable."""
        from omoi_os.workers.spec_state_machine import SpecStateMachine, _MockSpec

        machine = SpecStateMachine(
            spec_id="test-spec-123",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        # When database returns None and we detect mock DB, should return _MockSpec
        spec = await machine.load_spec()

        # Since the mock DB returns None and has _pending_operations marker,
        # it should create a mock spec
        assert spec is not None
        assert isinstance(spec, _MockSpec)
        assert spec.id == "test-spec-123"
        assert spec.is_mock is True

    @pytest.mark.asyncio
    async def test_load_spec_restores_checkpoint(self, mock_db, temp_workspace):
        """Test load_spec restores from checkpoint file if it exists."""
        from omoi_os.workers.spec_state_machine import SpecStateMachine, _MockSpec

        # Create a checkpoint file
        checkpoint_dir = Path(temp_workspace) / ".omoi_os" / "checkpoints"
        checkpoint_dir.mkdir(parents=True)
        (checkpoint_dir / "state.json").write_text(json.dumps({
            "title": "My Spec",
            "description": "A test spec",
            "current_phase": "requirements",
            "phase_data": {"explore": {"project_type": "web_app"}},
            "phase_attempts": {"explore": 1},
            "session_transcripts": {},
        }))

        machine = SpecStateMachine(
            spec_id="test-spec-123",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        spec = await machine.load_spec()

        assert isinstance(spec, _MockSpec)
        assert spec.title == "My Spec"
        assert spec.current_phase == "requirements"
        assert spec.phase_data["explore"]["project_type"] == "web_app"

    @pytest.mark.asyncio
    async def test_file_checkpoints_work(self, mock_db, temp_workspace):
        """Test file-based checkpoints are created correctly."""
        from omoi_os.workers.spec_state_machine import SpecPhase, SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test-spec-123",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        # Write phase data
        await machine._write_file_checkpoint(
            SpecPhase.EXPLORE,
            {"project_type": "api", "tech_stack": ["python", "fastapi"]}
        )

        # Verify file was created
        phase_file = Path(temp_workspace) / ".omoi_os" / "phase_data" / "explore.json"
        assert phase_file.exists()

        # Verify content
        data = json.loads(phase_file.read_text())
        assert data["project_type"] == "api"
        assert "fastapi" in data["tech_stack"]

    @pytest.mark.asyncio
    async def test_save_checkpoint_creates_state_file(self, mock_db, temp_workspace):
        """Test save_checkpoint creates the state.json file."""
        from omoi_os.workers.spec_state_machine import SpecStateMachine, _MockSpec

        machine = SpecStateMachine(
            spec_id="test-spec-123",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        mock_spec = _MockSpec("test-spec-123", "Test Title", "Test Description")
        mock_spec.current_phase = "design"
        mock_spec.phase_data = {"explore": {"data": 1}, "requirements": {"data": 2}}
        mock_spec.phase_attempts = {"explore": 1, "requirements": 2}

        await machine.save_checkpoint(mock_spec)

        # Verify state file
        state_file = Path(temp_workspace) / ".omoi_os" / "checkpoints" / "state.json"
        assert state_file.exists()

        state = json.loads(state_file.read_text())
        assert state["current_phase"] == "design"
        assert state["spec_id"] == "test-spec-123"
        # completed_phases should include explore and requirements (before design)
        assert "explore" in state.get("completed_phases", [])
        assert "requirements" in state.get("completed_phases", [])


class TestSpecStateMachineEvaluators:
    """Test evaluator integration in the state machine."""

    @pytest.fixture
    def temp_workspace(self):
        workspace = tempfile.mkdtemp(prefix="spec_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db._pending_operations = []
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)
        return db

    def test_evaluators_are_initialized(self, mock_db, temp_workspace):
        """Test all phase evaluators are properly initialized."""
        from omoi_os.evals import (
            DesignEvaluator,
            ExplorationEvaluator,
            RequirementEvaluator,
            TaskEvaluator,
        )
        from omoi_os.workers.spec_state_machine import SpecPhase, SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        assert isinstance(machine.evaluators[SpecPhase.EXPLORE], ExplorationEvaluator)
        assert isinstance(machine.evaluators[SpecPhase.REQUIREMENTS], RequirementEvaluator)
        assert isinstance(machine.evaluators[SpecPhase.DESIGN], DesignEvaluator)
        assert isinstance(machine.evaluators[SpecPhase.TASKS], TaskEvaluator)

    def test_evaluator_passes_valid_output(self, mock_db, temp_workspace):
        """Test that valid phase outputs pass evaluation."""
        from omoi_os.workers.spec_state_machine import SpecPhase, SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        # Create fully valid exploration output (all required fields)
        explore_output = {
            "project_type": "web_app",
            "tech_stack": ["python", "fastapi", "postgresql"],
            "existing_models": [
                {"name": "User", "file": "models.py", "fields": ["id", "email"]},
            ],
            "existing_routes": ["/api/users", "/api/health"],
            "database_type": "postgresql",
            # Fields needed by evaluator
            "project_structure": {
                "directories": ["src/", "tests/", "docs/"],
                "entry_point": "main.py",
            },
            "coding_conventions": {
                "style_guide": "pep8",
                "naming": "snake_case",
            },
            "explored_files": ["main.py", "models.py", "routes.py"],
        }

        # Use the evaluator directly (evaluators are stored in machine.evaluators)
        evaluator = machine.evaluators[SpecPhase.EXPLORE]
        result = evaluator.evaluate(explore_output)
        # Should pass or have high enough score
        assert result.passed or result.score >= 0.7, (
            f"Expected pass or score >= 0.7, got score={result.score}, "
            f"failures={result.failures}"
        )

    def test_evaluator_fails_empty_output(self, mock_db, temp_workspace):
        """Test that empty outputs fail evaluation."""
        from omoi_os.workers.spec_state_machine import SpecPhase, SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        evaluator = machine.evaluators[SpecPhase.EXPLORE]
        result = evaluator.evaluate({})
        assert not result.passed
        assert len(result.failures) > 0


class TestSpecStateMachinePrompts:
    """Test prompt generation for phases."""

    @pytest.fixture
    def temp_workspace(self):
        workspace = tempfile.mkdtemp(prefix="spec_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db._pending_operations = []
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)
        return db

    @pytest.fixture
    def mock_spec(self):
        """Create a mock spec for prompt testing."""
        from omoi_os.workers.spec_state_machine import _MockSpec
        spec = _MockSpec("test-123", "Test Feature", "Implement user authentication")
        return spec

    def test_explore_prompt_includes_spec_info(self, mock_db, temp_workspace, mock_spec):
        """Test explore prompt includes spec title and description."""
        from omoi_os.workers.spec_state_machine import SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        prompt = machine._get_explore_prompt(mock_spec)

        assert "Test Feature" in prompt
        assert "authentication" in prompt.lower()
        assert len(prompt) > 100  # Should be substantive

    def test_requirements_prompt_builds_correctly(self, mock_db, temp_workspace, mock_spec):
        """Test requirements prompt includes exploration data."""
        from omoi_os.workers.spec_state_machine import SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        phase_data = {
            "explore": {
                "project_type": "web_app",
                "tech_stack": ["python"],
            }
        }

        prompt = machine._get_requirements_prompt(mock_spec, phase_data)

        assert "Test Feature" in prompt
        assert len(prompt) > 100

    def test_retry_prompt_includes_failures(self, mock_db, temp_workspace, mock_spec):
        """Test retry prompt includes failure information."""
        from omoi_os.evals.base import EvalResult
        from omoi_os.workers.spec_state_machine import SpecPhase, SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        eval_result = EvalResult(
            passed=False,
            score=0.4,
            failures=["Missing project_type", "Empty tech_stack"],
            feedback_for_retry="Please include project_type and tech_stack.",
        )

        retry_prompt = machine.build_retry_prompt(
            phase=SpecPhase.EXPLORE,
            spec=mock_spec,
            previous_output={"incomplete": "data"},
            eval_result=eval_result,
        )

        assert len(retry_prompt) > 50
        assert "retry" in retry_prompt.lower() or "fix" in retry_prompt.lower()


class TestSpecStateMachinePhaseTransitions:
    """Test phase transitions and state management."""

    @pytest.fixture
    def temp_workspace(self):
        workspace = tempfile.mkdtemp(prefix="spec_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db._pending_operations = []
        db.commit = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=mock_result)
        return db

    def test_next_phase_returns_correct_sequence(self, mock_db, temp_workspace):
        """Test next_phase returns the correct next phase."""
        from omoi_os.workers.spec_state_machine import SpecPhase, SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        assert machine.next_phase(SpecPhase.EXPLORE) == SpecPhase.REQUIREMENTS
        assert machine.next_phase(SpecPhase.REQUIREMENTS) == SpecPhase.DESIGN
        assert machine.next_phase(SpecPhase.DESIGN) == SpecPhase.TASKS
        assert machine.next_phase(SpecPhase.TASKS) == SpecPhase.SYNC
        assert machine.next_phase(SpecPhase.SYNC) == SpecPhase.COMPLETE
        assert machine.next_phase(SpecPhase.COMPLETE) == SpecPhase.COMPLETE

    def test_phase_order_is_correct(self, mock_db, temp_workspace):
        """Test PHASE_ORDER list is correct."""
        from omoi_os.workers.spec_state_machine import SpecPhase, SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        expected = [
            SpecPhase.EXPLORE,
            SpecPhase.REQUIREMENTS,
            SpecPhase.DESIGN,
            SpecPhase.TASKS,
            SpecPhase.SYNC,
            SpecPhase.COMPLETE,
        ]

        assert machine.PHASE_ORDER == expected

    def test_phase_timeouts_are_reasonable(self, mock_db, temp_workspace):
        """Test phase timeouts are reasonable values."""
        from omoi_os.workers.spec_state_machine import SpecPhase, SpecStateMachine

        machine = SpecStateMachine(
            spec_id="test",
            db_session=mock_db,
            working_directory=temp_workspace,
        )

        for phase, timeout in machine.PHASE_TIMEOUTS.items():
            assert timeout >= 60, f"{phase} timeout too short"
            assert timeout <= 600, f"{phase} timeout too long"


class TestWorkerPhaseAwareRouting:
    """Test the worker routes correctly based on environment variables."""

    @pytest.fixture
    def temp_workspace(self):
        workspace = tempfile.mkdtemp(prefix="worker_test_")
        yield workspace
        shutil.rmtree(workspace, ignore_errors=True)

    def test_worker_config_reads_spec_env_vars(self):
        """Test WorkerConfig reads SPEC_ID and SPEC_PHASE env vars."""
        import base64

        # Set up environment
        env = {
            "SPEC_ID": "spec-test-123",
            "SPEC_PHASE": "explore",
            "PHASE_DATA_B64": base64.b64encode(
                json.dumps({"previous": "data"}).encode()
            ).decode(),
        }

        with patch.dict(os.environ, env, clear=False):
            from omoi_os.workers.claude_sandbox_worker import WorkerConfig

            config = WorkerConfig()

            assert config.spec_id == "spec-test-123"
            assert config.spec_phase == "explore"
            assert config.phase_data == {"previous": "data"}

    def test_worker_config_handles_missing_env_vars(self):
        """Test WorkerConfig handles missing SPEC_* env vars gracefully."""
        # Clear the env vars
        env = {}
        for key in ["SPEC_ID", "SPEC_PHASE", "PHASE_DATA_B64"]:
            env[key] = ""

        with patch.dict(os.environ, env, clear=False):
            # Need to force reimport to pick up new env
            # Just verify the attributes exist and are empty
            from omoi_os.workers.claude_sandbox_worker import WorkerConfig

            # Create config without spec vars set
            original_spec_id = os.environ.pop("SPEC_ID", None)
            original_spec_phase = os.environ.pop("SPEC_PHASE", None)
            original_phase_data = os.environ.pop("PHASE_DATA_B64", None)

            try:
                config = WorkerConfig()
                assert config.spec_id is None or config.spec_id == ""
                assert config.spec_phase is None or config.spec_phase == ""
            finally:
                if original_spec_id:
                    os.environ["SPEC_ID"] = original_spec_id
                if original_spec_phase:
                    os.environ["SPEC_PHASE"] = original_spec_phase
                if original_phase_data:
                    os.environ["PHASE_DATA_B64"] = original_phase_data

    def test_worker_config_decodes_phase_data(self):
        """Test WorkerConfig decodes PHASE_DATA_B64 correctly."""
        import base64

        phase_data = {
            "explore": {"project_type": "web_app"},
            "requirements": {"reqs": ["auth", "api"]},
        }
        encoded = base64.b64encode(json.dumps(phase_data).encode()).decode()

        with patch.dict(os.environ, {
            "SPEC_ID": "test",
            "SPEC_PHASE": "design",
            "PHASE_DATA_B64": encoded,
        }, clear=False):
            from omoi_os.workers.claude_sandbox_worker import WorkerConfig

            config = WorkerConfig()

            assert config.phase_data["explore"]["project_type"] == "web_app"
            assert "auth" in config.phase_data["requirements"]["reqs"]
