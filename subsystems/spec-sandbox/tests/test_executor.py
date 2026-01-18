"""Tests for Claude executor."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from spec_sandbox.executor.claude_executor import (
    ClaudeExecutor,
    ExecutorConfig,
    ExecutionResult,
)
from spec_sandbox.reporters.array import ArrayReporter
from spec_sandbox.schemas.spec import SpecPhase


@pytest.fixture
def executor_config():
    """Create test executor config with mock mode enabled."""
    return ExecutorConfig(
        model="claude-sonnet-4-5-20250929",
        max_turns=10,
        max_budget_usd=1.0,
        use_mock=True,  # Use mock for fast tests
    )


@pytest.fixture
def reporter():
    """Create array reporter for testing."""
    return ArrayReporter()


@pytest.fixture
def executor(executor_config, reporter):
    """Create executor with test config."""
    return ClaudeExecutor(
        config=executor_config,
        reporter=reporter,
        spec_id="test-spec",
    )


class TestClaudeExecutor:
    """Test suite for ClaudeExecutor."""

    @pytest.mark.asyncio
    async def test_execute_phase_mock_mode(self, executor):
        """Test mock execution when use_mock is enabled."""
        result = await executor.execute_phase(
            phase=SpecPhase.EXPLORE,
            spec_title="Test Feature",
            spec_description="Build a test feature",
        )

        assert result.success is True
        assert "_mock" in result.output
        assert result.output["_mock"] is True
        assert "codebase_summary" in result.output

    @pytest.mark.asyncio
    async def test_execute_all_phases_mock(self, executor):
        """Test that all phases can execute in mock mode."""
        context = {}

        for phase in SpecPhase:
            result = await executor.execute_phase(
                phase=phase,
                spec_title="Test",
                spec_description="Test description",
                context=context,
            )

            assert result.success is True
            assert result.output is not None

            # Accumulate context for next phase
            context[phase.value] = result.output

    @pytest.mark.asyncio
    async def test_execute_phase_emits_progress(self, executor, reporter):
        """Test that execution emits progress events."""
        await executor.execute_phase(
            phase=SpecPhase.EXPLORE,
            spec_title="Test",
            spec_description="Test",
        )

        # Should have emitted at least one progress event
        progress_events = reporter.get_events_by_type("spec.progress")
        assert len(progress_events) >= 1

    @pytest.mark.asyncio
    async def test_build_prompt_includes_context(self, executor):
        """Test that prompt includes previous phase context."""
        context = {
            "explore": {"codebase_summary": "Test codebase"},
            "requirements": {"requirements": [{"id": "REQ-001"}]},
        }

        prompt = executor._build_prompt(
            phase=SpecPhase.DESIGN,
            spec_title="Test Feature",
            spec_description="Build X",
            context=context,
        )

        # Prompt should include context from previous phases
        assert "Test codebase" in prompt
        assert "REQ-001" in prompt
        assert "Test Feature" in prompt
        assert "Build X" in prompt

    def test_extract_json_from_code_block(self, executor):
        """Test JSON extraction from markdown code blocks."""
        text = '''
Here is the analysis:

```json
{
    "key": "value",
    "number": 42
}
```

That's the output.
'''
        result = executor._extract_json(text)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_from_bare_json(self, executor):
        """Test JSON extraction from bare JSON in text."""
        text = 'The result is {"status": "ok", "count": 5} as expected.'

        result = executor._extract_json(text)
        assert result == {"status": "ok", "count": 5}

    def test_extract_json_handles_nested(self, executor):
        """Test JSON extraction with nested objects."""
        text = '''
{"outer": {"inner": {"deep": true}}, "array": [1, 2, 3]}
'''
        result = executor._extract_json(text)
        assert result["outer"]["inner"]["deep"] is True
        assert result["array"] == [1, 2, 3]

    def test_extract_json_handles_invalid(self, executor):
        """Test JSON extraction returns error for invalid JSON."""
        text = "No JSON here, just plain text."

        result = executor._extract_json(text)
        assert "raw_text" in result
        assert "parse_error" in result

    def test_get_system_prompt_includes_phase(self, executor):
        """Test system prompt includes phase name and output file."""
        from pathlib import Path

        output_file = Path("/tmp/test_output.json")
        prompt = executor._get_system_prompt(SpecPhase.REQUIREMENTS, output_file)
        assert "requirements" in prompt.lower()
        assert "JSON" in prompt
        assert str(output_file) in prompt


class TestExecutorConfig:
    """Test ExecutorConfig defaults and customization."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ExecutorConfig()

        assert config.model == "claude-sonnet-4-5-20250929"
        assert config.max_turns == 45  # Higher for exploration + write
        assert config.max_budget_usd == 20.0  # Allow thorough exploration
        assert "Read" in config.allowed_tools
        assert "Write" in config.allowed_tools
        assert "Task" in config.allowed_tools  # For exploration subagent
        assert "Explore" in config.allowed_tools  # Direct exploration tool
        assert "Agent" in config.allowed_tools  # For agent orchestration
        assert "Skill" in config.allowed_tools  # For skill invocation

    def test_custom_config(self):
        """Test custom configuration."""
        config = ExecutorConfig(
            model="custom-model",
            max_turns=100,
            max_budget_usd=20.0,
            allowed_tools=["Read"],
        )

        assert config.model == "custom-model"
        assert config.max_turns == 100
        assert config.max_budget_usd == 20.0
        assert config.allowed_tools == ["Read"]


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_success_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            output={"key": "value"},
            cost_usd=0.05,
            duration_ms=1500,
            tool_uses=3,
        )

        assert result.success is True
        assert result.output == {"key": "value"}
        assert result.error is None

    def test_failure_result(self):
        """Test failed execution result."""
        result = ExecutionResult(
            success=False,
            error="Something went wrong",
            duration_ms=500,
        )

        assert result.success is False
        assert result.error == "Something went wrong"
        assert result.output == {}


class TestPromptBuilding:
    """Test prompt building for each phase."""

    @pytest.fixture
    def executor(self):
        return ClaudeExecutor()

    def test_explore_prompt_structure(self, executor):
        """Test EXPLORE phase prompt has correct structure."""
        prompt = executor._build_prompt(
            phase=SpecPhase.EXPLORE,
            spec_title="Test",
            spec_description="Test desc",
            context={},
        )

        # Should have key sections
        assert "Spec Context" in prompt
        assert "Your Task" in prompt
        assert "Required Output Format" in prompt
        assert "codebase_summary" in prompt

    def test_requirements_prompt_includes_explore_context(self, executor):
        """Test REQUIREMENTS prompt includes EXPLORE context."""
        context = {"explore": {"tech_stack": ["Python", "FastAPI"]}}

        prompt = executor._build_prompt(
            phase=SpecPhase.REQUIREMENTS,
            spec_title="Test",
            spec_description="Test",
            context=context,
        )

        assert "Python" in prompt
        assert "FastAPI" in prompt
        assert "EARS" in prompt  # Requirements format

    def test_tasks_prompt_includes_all_prior_context(self, executor):
        """Test TASKS prompt includes all prior phase context."""
        context = {
            "explore": {"project_type": "web_app"},
            "requirements": {"requirements": [{"id": "REQ-001"}]},
            "design": {"components": [{"name": "API"}]},
        }

        prompt = executor._build_prompt(
            phase=SpecPhase.TASKS,
            spec_title="Test",
            spec_description="Test",
            context=context,
        )

        assert "web_app" in prompt
        assert "REQ-001" in prompt
        assert "API" in prompt
