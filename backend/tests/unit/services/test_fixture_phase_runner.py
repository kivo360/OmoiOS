"""Tests for spec pipeline fixture mode."""

import json
import pytest
from omoi_os.services.fixture_phase_runner import (
    FixturePhaseRunner,
    PhaseResult,
    PipelineResult,
    PHASE_EXPECTED_KEYS,
)


@pytest.fixture
def fixture_dir(tmp_path):
    """Create a temp directory with sample fixture files."""
    # Explore fixture - must include expected keys from PHASE_EXPECTED_KEYS
    explore = {
        "project_type": "web_api",
        "structure": {"src/": "Source code"},
        "conventions": {"naming": "snake_case"},
    }
    (tmp_path / "explore_output.json").write_text(json.dumps(explore))

    # Requirements fixture
    requirements = {
        "requirements": [
            {"id": "REQ-001", "text": "The system SHALL authenticate users"},
        ],
    }
    (tmp_path / "requirements_output.json").write_text(json.dumps(requirements))

    # Design fixture
    design = {
        "components": [{"name": "AuthService", "responsibility": "Handle auth"}],
        "architecture": {"style": "layered"},
    }
    (tmp_path / "design_output.json").write_text(json.dumps(design))

    # Tasks fixture
    tasks = {
        "tasks": [
            {"id": "TSK-001", "title": "Implement auth", "type": "implementation"},
        ],
    }
    (tmp_path / "tasks_output.json").write_text(json.dumps(tasks))

    return tmp_path


class TestPhaseResult:
    def test_creation(self):
        r = PhaseResult(phase="explore", output={}, passed=True, score=0.9)
        assert r.phase == "explore"
        assert r.passed is True
        assert r.issues == []

    def test_with_error(self):
        r = PhaseResult(
            phase="explore", output={}, passed=False, score=0.0, error="Not found"
        )
        assert r.error == "Not found"


class TestPipelineResult:
    def test_creation(self):
        r = PipelineResult(
            phases_run=["explore", "requirements"],
            phases_passed=["explore"],
            all_passed=False,
            results=[],
        )
        assert not r.all_passed


class TestFixturePhaseRunner:
    def test_list_available_fixtures(self, fixture_dir):
        runner = FixturePhaseRunner(fixture_dir=str(fixture_dir))
        available = runner.list_available_fixtures()
        assert "explore" in available
        assert "requirements" in available
        assert "design" in available
        assert "tasks" in available

    def test_list_empty_dir(self, tmp_path):
        runner = FixturePhaseRunner(fixture_dir=str(tmp_path))
        available = runner.list_available_fixtures()
        assert available == []

    @pytest.mark.asyncio
    async def test_run_phase_explore(self, fixture_dir):
        runner = FixturePhaseRunner(fixture_dir=str(fixture_dir))
        runner._evaluators = {}  # Force structural validation only
        result = await runner.run_phase("explore")
        assert result.passed is True
        assert result.score == 1.0
        assert result.phase == "explore"

    @pytest.mark.asyncio
    async def test_run_phase_missing_fixture(self, tmp_path):
        runner = FixturePhaseRunner(fixture_dir=str(tmp_path))
        result = await runner.run_phase("explore")
        assert result.passed is False
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_run_phase_partial_fixture(self, tmp_path):
        """Fixture with some missing keys should get partial score."""
        partial = {"project_type": "test"}  # Missing structure and conventions
        (tmp_path / "explore_output.json").write_text(json.dumps(partial))
        runner = FixturePhaseRunner(fixture_dir=str(tmp_path))
        runner._evaluators = {}  # Force structural validation only
        result = await runner.run_phase("explore")
        assert result.score < 1.0
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_run_full_pipeline(self, fixture_dir):
        runner = FixturePhaseRunner(fixture_dir=str(fixture_dir))
        runner._evaluators = {}  # Force structural validation only
        result = await runner.run_full_pipeline()
        assert result.all_passed is True
        assert len(result.phases_run) == 4
        assert len(result.phases_passed) == 4

    @pytest.mark.asyncio
    async def test_run_full_pipeline_stops_on_failure(self, tmp_path):
        """Pipeline stops at first failing phase."""
        # Create only explore with missing keys
        (tmp_path / "explore_output.json").write_text(json.dumps({}))
        (tmp_path / "requirements_output.json").write_text(
            json.dumps({"requirements": []})
        )

        runner = FixturePhaseRunner(fixture_dir=str(tmp_path))
        result = await runner.run_full_pipeline()
        assert not result.all_passed
        assert len(result.phases_run) == 1  # Stopped after explore failed

    @pytest.mark.asyncio
    async def test_run_full_pipeline_empty_dir(self, tmp_path):
        runner = FixturePhaseRunner(fixture_dir=str(tmp_path))
        result = await runner.run_full_pipeline()
        assert not result.all_passed
        assert len(result.phases_run) == 0

    def test_validate_structure_complete(self, fixture_dir):
        runner = FixturePhaseRunner(fixture_dir=str(fixture_dir))
        fixture = json.loads((fixture_dir / "explore_output.json").read_text())
        score, issues = runner._validate_structure("explore", fixture)
        assert score == 1.0
        assert issues == []

    def test_validate_structure_incomplete(self, fixture_dir):
        runner = FixturePhaseRunner(fixture_dir=str(fixture_dir))
        score, issues = runner._validate_structure("explore", {"project_type": "test"})
        assert score < 1.0
        assert len(issues) > 0

    def test_phase_expected_keys_defined(self):
        assert "explore" in PHASE_EXPECTED_KEYS
        assert "requirements" in PHASE_EXPECTED_KEYS
        assert "design" in PHASE_EXPECTED_KEYS
        assert "tasks" in PHASE_EXPECTED_KEYS
