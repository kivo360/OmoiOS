"""Unit tests for claude_sandbox_worker.py.

Tests the standalone components of the sandbox worker:
- IterationState: dataclass state tracking and serialization
- FileChangeTracker: diff generation for file edits
- WorkerConfig: environment variable parsing and configuration
- EventReporter: HTTP event reporting with error handling
- MessagePoller: message polling from the main server
- check_git_status: git state validation
- check_spec_output: spec file validation with frontmatter checking
- find_dependency_files: recursive dependency file discovery
- install_project_dependencies: automatic dependency installation
"""

import base64
import json
import os
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from omoi_os.workers.claude_sandbox_worker import (
    AgentDefinition,
    EventReporter,
    FileChangeTracker,
    IterationState,
    MessagePoller,
    WorkerConfig,
    check_git_status,
    check_spec_output,
    find_dependency_files,
    install_project_dependencies,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def clean_env():
    """Provide a minimal clean environment for WorkerConfig tests.

    Preserves PATH and HOME but clears worker-specific env vars.
    """
    worker_vars = [
        "SANDBOX_ID",
        "TASK_ID",
        "AGENT_ID",
        "TICKET_ID",
        "TICKET_TITLE",
        "TICKET_DESCRIPTION",
        "TASK_DATA_BASE64",
        "CALLBACK_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
        "MODEL",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_BASE_URL",
        "INITIAL_PROMPT",
        "POLL_INTERVAL",
        "HEARTBEAT_INTERVAL",
        "MAX_TURNS",
        "MAX_BUDGET_USD",
        "PERMISSION_MODE",
        "CWD",
        "SYSTEM_PROMPT",
        "SYSTEM_PROMPT_APPEND",
        "ALLOWED_TOOLS",
        "DISALLOWED_TOOLS",
        "ENABLE_ASK_USER_QUESTION",
        "ENABLE_SKILLS",
        "ENABLE_SUBAGENTS",
        "EXECUTION_MODE",
        "AGENT_TYPE",
        "REQUIRE_SPEC_SKILL",
        "GITHUB_TOKEN",
        "GITHUB_REPO",
        "BRANCH_NAME",
        "PREVIEW_ENABLED",
        "PREVIEW_PORT",
        "RESUME_SESSION_ID",
        "FORK_SESSION",
        "SESSION_TRANSCRIPT_B64",
        "CONVERSATION_CONTEXT",
        "SETTING_SOURCES",
    ]
    saved = {k: os.environ.pop(k) for k in worker_vars if k in os.environ}
    yield
    # Restore
    for k, v in saved.items():
        os.environ[k] = v


@pytest.fixture
def mock_worker_config():
    """Create a minimal WorkerConfig mock for classes that need it."""
    config = MagicMock(spec=WorkerConfig)
    config.sandbox_id = "sb-test-001"
    config.callback_url = "http://localhost:8000"
    config.task_id = "task-123"
    config.agent_id = "agent-456"
    config.require_spec_skill = False
    return config


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace directory for file-based tests."""
    return tmp_path


@pytest.fixture
def tmp_git_workspace(tmp_path):
    """Create a temporary workspace with a git repo."""
    import subprocess

    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    # Create initial commit so HEAD exists
    (tmp_path / "README.md").write_text("# test")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    return tmp_path


# ============================================================================
# Tests: AgentDefinition
# ============================================================================


class TestAgentDefinition:
    """Tests for the AgentDefinition dataclass."""

    def test_create_with_required_fields(self):
        agent = AgentDefinition(
            description="Test agent",
            prompt="Do something",
            tools=["Bash", "Read"],
        )
        assert agent.description == "Test agent"
        assert agent.prompt == "Do something"
        assert agent.tools == ["Bash", "Read"]
        assert agent.model is None

    def test_create_with_model(self):
        agent = AgentDefinition(
            description="Custom",
            prompt="Run",
            tools=["Write"],
            model="claude-sonnet-4-20250514",
        )
        assert agent.model == "claude-sonnet-4-20250514"


# ============================================================================
# Tests: IterationState
# ============================================================================


class TestIterationState:
    """Tests for IterationState dataclass and serialization."""

    def test_default_values(self):
        state = IterationState()
        assert state.iteration_num == 0
        assert state.successful_iterations == 0
        assert state.error_count == 0
        assert state.total_cost == 0.0
        assert state.completion_signal_count == 0
        assert state.start_time is None
        assert state.last_session_id is None
        assert state.validation_passed is False
        assert state.tests_passed is False
        assert state.code_committed is False
        assert state.code_pushed is False
        assert state.pr_created is False
        assert state.pr_url is None
        assert state.pr_number is None
        assert state.files_changed == 0
        assert state.ci_status is None

    def test_to_event_data_with_start_time(self):
        state = IterationState()
        state.start_time = time.time() - 10  # Started 10 seconds ago
        state.iteration_num = 3
        state.successful_iterations = 2
        state.error_count = 1
        state.total_cost = 1.5
        state.validation_passed = True
        state.tests_passed = True
        state.code_committed = True
        state.code_pushed = True
        state.pr_created = True
        state.pr_url = "https://github.com/owner/repo/pull/42"
        state.pr_number = 42
        state.files_changed = 5

        data = state.to_event_data()

        assert data["iteration_num"] == 3
        assert data["successful_iterations"] == 2
        assert data["error_count"] == 1
        assert data["total_cost_usd"] == 1.5
        assert data["elapsed_seconds"] >= 10
        assert data["validation_passed"] is True
        assert data["tests_passed"] is True
        assert data["code_committed"] is True
        assert data["code_pushed"] is True
        assert data["pr_created"] is True
        assert data["pr_url"] == "https://github.com/owner/repo/pull/42"
        assert data["pr_number"] == 42
        assert data["files_changed"] == 5

    def test_to_event_data_without_start_time(self):
        state = IterationState()
        data = state.to_event_data()
        assert data["elapsed_seconds"] == 0


# ============================================================================
# Tests: FileChangeTracker
# ============================================================================


class TestFileChangeTracker:
    """Tests for FileChangeTracker diff generation."""

    def test_new_file_diff(self):
        tracker = FileChangeTracker()
        diff = tracker.generate_diff("/workspace/new.py", "print('hello')\n")

        assert diff["file_path"] == "/workspace/new.py"
        assert diff["change_type"] == "created"
        assert diff["lines_added"] >= 1
        assert diff["lines_removed"] == 0
        assert "+print('hello')" in diff["diff_preview"]

    def test_modified_file_diff(self):
        tracker = FileChangeTracker()
        tracker.cache_file_before_edit("/workspace/app.py", "old line\n")
        diff = tracker.generate_diff("/workspace/app.py", "new line\n")

        assert diff["change_type"] == "modified"
        assert diff["lines_added"] >= 1
        assert diff["lines_removed"] >= 1
        assert (
            "a//workspace/app.py" in diff["diff_preview"]
            or "-old line" in diff["diff_preview"]
        )

    def test_no_changes_diff(self):
        tracker = FileChangeTracker()
        content = "same content\n"
        tracker.cache_file_before_edit("/workspace/same.py", content)
        diff = tracker.generate_diff("/workspace/same.py", content)

        assert diff["change_type"] == "modified"
        assert diff["lines_added"] == 0
        assert diff["lines_removed"] == 0

    def test_cache_consumed_after_diff(self):
        """Cache entry should be consumed (removed) after generating diff."""
        tracker = FileChangeTracker()
        tracker.cache_file_before_edit("/workspace/file.py", "cached")
        tracker.generate_diff("/workspace/file.py", "new content")

        # Second call should treat it as a new file since cache was consumed
        diff = tracker.generate_diff("/workspace/file.py", "another version")
        assert diff["change_type"] == "created"

    def test_large_diff_truncated(self):
        tracker = FileChangeTracker()
        # Create content large enough to trigger truncation
        large_content = "\n".join(f"line {i}" for i in range(200))
        diff = tracker.generate_diff("/workspace/big.py", large_content)

        assert diff["diff_preview"] is not None
        assert len(diff["diff_preview"]) <= 5000

    def test_multiline_diff(self):
        tracker = FileChangeTracker()
        old = "line1\nline2\nline3\n"
        new = "line1\nmodified\nline3\nnew_line4\n"
        tracker.cache_file_before_edit("/workspace/multi.py", old)
        diff = tracker.generate_diff("/workspace/multi.py", new)

        assert diff["change_type"] == "modified"
        assert diff["lines_added"] >= 2  # "modified" + "new_line4"
        assert diff["lines_removed"] >= 1  # "line2"


# ============================================================================
# Tests: WorkerConfig
# ============================================================================


class TestWorkerConfig:
    """Tests for WorkerConfig environment variable parsing."""

    def test_defaults(self, clean_env):
        """WorkerConfig should have sane defaults when no env vars are set."""
        env = {"ANTHROPIC_API_KEY": "test-key"}  # pragma: allowlist secret
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.sandbox_id.startswith("sandbox-")
        assert config.task_id == ""
        assert config.agent_id == ""
        assert config.callback_url == "http://localhost:8000"
        assert config.max_turns == 50
        assert config.max_budget_usd == 10.0
        assert config.permission_mode == "bypassPermissions"
        assert config.cwd == "/workspace"
        assert config.poll_interval == 0.5
        assert config.heartbeat_interval == 30
        assert config.execution_mode == "implementation"
        assert config.agent_type == "implementer"
        assert config.require_spec_skill is False

    def test_explicit_env_vars(self, clean_env):
        """WorkerConfig should read explicit environment variables."""
        env = {
            "SANDBOX_ID": "my-sandbox",
            "TASK_ID": "task-99",
            "AGENT_ID": "agent-7",
            "TICKET_ID": "TKT-001",
            "TICKET_TITLE": "Fix auth bug",
            "CALLBACK_URL": "https://api.example.com",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
            "MAX_TURNS": "100",
            "MAX_BUDGET_USD": "25.0",
            "POLL_INTERVAL": "2.0",
            "HEARTBEAT_INTERVAL": "60",
            "CWD": "/home/user/project",
            "EXECUTION_MODE": "exploration",
            "AGENT_TYPE": "validator",
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.sandbox_id == "my-sandbox"
        assert config.task_id == "task-99"
        assert config.agent_id == "agent-7"
        assert config.ticket_id == "TKT-001"
        assert config.ticket_title == "Fix auth bug"
        assert config.callback_url == "https://api.example.com"
        assert config.api_key == "test-key"  # pragma: allowlist secret
        assert config.max_turns == 100
        assert config.max_budget_usd == 25.0
        assert config.poll_interval == 2.0
        assert config.heartbeat_interval == 60
        assert config.cwd == "/home/user/project"
        assert config.execution_mode == "exploration"
        assert config.agent_type == "validator"

    def test_task_data_base64_decoding(self, clean_env):
        """WorkerConfig should decode TASK_DATA_BASE64 and extract fields."""
        task_data = {
            "task": {"id": "task-from-b64", "description": "Implement login"},
            "ticket": {
                "id": "TKT-010",
                "title": "Auth feature",
                "description": "Full auth",
            },
            "spec": {"id": "spec-001", "spec_task_id": "stask-001"},
            "requirements": [
                {
                    "id": "REQ-001",
                    "acceptance_criteria": [
                        {"id": "AC-001", "text": "User can login", "completed": False},
                    ],
                }
            ],
            "_markdown_context": "## Auth Feature\nFull spec here.",
        }
        b64 = base64.b64encode(json.dumps(task_data).encode()).decode()

        env = {
            "TASK_DATA_BASE64": b64,
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.task_id == "task-from-b64"
        assert config.task_description == "Implement login"
        assert config.ticket_id == "TKT-010"
        assert config.ticket_title == "Auth feature"
        assert config.has_spec_context is True
        assert len(config.acceptance_criteria) == 1
        assert config.acceptance_criteria[0]["id"] == "AC-001"
        assert config.spec_context_markdown == "## Auth Feature\nFull spec here."

    def test_task_data_base64_invalid(self, clean_env):
        """WorkerConfig should handle invalid TASK_DATA_BASE64 gracefully."""
        env = {
            "TASK_DATA_BASE64": "not-valid-base64!!!",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.task_data == {}
        assert config.task_description == ""

    def test_allowed_tools_replace_mode(self, clean_env):
        """ALLOWED_TOOLS should replace SDK defaults."""
        env = {
            "ALLOWED_TOOLS": "Read,Write,Bash",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.allowed_tools == ["Read", "Write", "Bash"]
        assert config.tools_mode == "replace"

    def test_default_tools_mode(self, clean_env):
        """Without ALLOWED_TOOLS, should use SDK defaults."""
        env = {"ANTHROPIC_API_KEY": "test-key"}  # pragma: allowlist secret
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.allowed_tools is None
        assert config.tools_mode == "default"

    def test_disallowed_tools_default(self, clean_env):
        """AskUserQuestion should be disallowed by default."""
        env = {"ANTHROPIC_API_KEY": "test-key"}  # pragma: allowlist secret
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert "AskUserQuestion" in config.disallowed_tools

    def test_disallowed_tools_merged(self, clean_env):
        """DISALLOWED_TOOLS should merge with defaults."""
        env = {
            "DISALLOWED_TOOLS": "Bash,Write",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert "AskUserQuestion" in config.disallowed_tools
        assert "Bash" in config.disallowed_tools
        assert "Write" in config.disallowed_tools

    def test_enable_ask_user_question(self, clean_env):
        """ENABLE_ASK_USER_QUESTION=true should remove it from disallowed."""
        env = {
            "ENABLE_ASK_USER_QUESTION": "true",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.disallowed_tools is None or "AskUserQuestion" not in (
            config.disallowed_tools or []
        )

    def test_require_spec_skill_true(self, clean_env):
        """REQUIRE_SPEC_SKILL=true should enable spec-driven dev."""
        env = {
            "REQUIRE_SPEC_SKILL": "true",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.require_spec_skill is True

    def test_require_spec_skill_false_by_default(self, clean_env):
        """REQUIRE_SPEC_SKILL should be false by default."""
        env = {"ANTHROPIC_API_KEY": "test-key"}  # pragma: allowlist secret
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.require_spec_skill is False

    def test_oauth_token_preferred(self, clean_env):
        """CLAUDE_CODE_OAUTH_TOKEN should be read."""
        env = {
            "CLAUDE_CODE_OAUTH_TOKEN": "oauth-token-123",
            "ANTHROPIC_API_KEY": "test-key-fallback",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.oauth_token == "oauth-token-123"
        assert config.api_key == "test-key-fallback"  # pragma: allowlist secret

    def test_env_vars_not_set_uses_env_defaults(self, clean_env):
        """Task/ticket fields should fallback from TASK_DATA_BASE64 to env vars."""
        env = {
            "TASK_ID": "env-task",
            "TICKET_ID": "env-ticket",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()

        assert config.task_id == "env-task"
        assert config.ticket_id == "env-ticket"


# ============================================================================
# Tests: EventReporter
# ============================================================================


class TestEventReporter:
    """Tests for EventReporter HTTP event reporting."""

    @pytest.mark.asyncio
    async def test_report_success(self, mock_worker_config):
        """Successful event report should return True."""
        reporter = EventReporter(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200

        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(return_value=mock_response)

        result = await reporter.report("agent.tool_use", {"tool": "Bash"})

        assert result is True
        assert reporter.event_count == 1
        reporter.client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_report_adds_core_identifiers(self, mock_worker_config):
        """Event data should include sandbox_id, task_id, agent_id."""
        reporter = EventReporter(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200

        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(return_value=mock_response)

        await reporter.report("test.event", {"custom": "data"})

        call_json = reporter.client.post.call_args[1]["json"]
        assert call_json["event_data"]["sandbox_id"] == "sb-test-001"
        assert call_json["event_data"]["task_id"] == "task-123"
        assert call_json["event_data"]["agent_id"] == "agent-456"
        assert call_json["event_data"]["custom"] == "data"

    @pytest.mark.asyncio
    async def test_report_posts_to_correct_url(self, mock_worker_config):
        """Events should be posted to /api/v1/sandboxes/{id}/events."""
        reporter = EventReporter(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200

        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(return_value=mock_response)

        await reporter.report("agent.heartbeat", {})

        url = reporter.client.post.call_args[0][0]
        assert url == "http://localhost:8000/api/v1/sandboxes/sb-test-001/events"

    @pytest.mark.asyncio
    async def test_report_failure_returns_false(self, mock_worker_config):
        """Non-200 response should return False."""
        reporter = EventReporter(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 500

        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(return_value=mock_response)

        result = await reporter.report("agent.error", {"error": "boom"})
        assert result is False

    @pytest.mark.asyncio
    async def test_report_502_silently_fails(self, mock_worker_config):
        """502 errors should silently fail without logging warnings."""
        reporter = EventReporter(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 502

        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(return_value=mock_response)

        result = await reporter.report("agent.heartbeat", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_report_network_error(self, mock_worker_config):
        """Network errors should return False without raising."""
        reporter = EventReporter(mock_worker_config)
        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection refused", request=MagicMock())
        )

        result = await reporter.report("agent.tool_use", {"tool": "Read"})
        assert result is False

    @pytest.mark.asyncio
    async def test_report_no_client(self, mock_worker_config):
        """Report should return False when client is not initialized."""
        reporter = EventReporter(mock_worker_config)
        # client is None by default
        result = await reporter.report("test.event", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_heartbeat(self, mock_worker_config):
        """Heartbeat should report agent.heartbeat with timestamp."""
        reporter = EventReporter(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200

        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(return_value=mock_response)

        result = await reporter.heartbeat()

        assert result is True
        call_json = reporter.client.post.call_args[1]["json"]
        assert call_json["event_type"] == "agent.heartbeat"
        assert call_json["source"] == "worker"
        assert "timestamp" in call_json["event_data"]

    @pytest.mark.asyncio
    async def test_report_criterion_met(self, mock_worker_config):
        """Should report spec.criterion_met event with correct data."""
        reporter = EventReporter(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200

        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(return_value=mock_response)

        result = await reporter.report_criterion_met(
            criterion_id="AC-001",
            requirement_id="REQ-001",
            evidence="Tests pass",
        )

        assert result is True
        call_json = reporter.client.post.call_args[1]["json"]
        assert call_json["event_type"] == "spec.criterion_met"
        assert call_json["event_data"]["criterion_id"] == "AC-001"
        assert call_json["event_data"]["requirement_id"] == "REQ-001"
        assert call_json["event_data"]["evidence"] == "Tests pass"

    @pytest.mark.asyncio
    async def test_event_count_increments(self, mock_worker_config):
        """Event count should increment with each report."""
        reporter = EventReporter(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200

        reporter.client = AsyncMock()
        reporter.client.post = AsyncMock(return_value=mock_response)

        await reporter.report("e1", {})
        await reporter.report("e2", {})
        await reporter.report("e3", {})

        assert reporter.event_count == 3

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_worker_config):
        """EventReporter should work as async context manager."""
        async with EventReporter(mock_worker_config) as reporter:
            assert reporter.client is not None

        # After exit, client should be closed
        # (httpx.AsyncClient.aclose is called)


# ============================================================================
# Tests: MessagePoller
# ============================================================================


class TestMessagePoller:
    """Tests for MessagePoller message retrieval."""

    @pytest.mark.asyncio
    async def test_poll_returns_messages(self, mock_worker_config):
        """Successful poll should return message list."""
        poller = MessagePoller(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"content": "Focus on auth", "message_type": "user_message"}
        ]

        poller.client = AsyncMock()
        poller.client.get = AsyncMock(return_value=mock_response)

        messages = await poller.poll()
        assert len(messages) == 1
        assert messages[0]["content"] == "Focus on auth"

    @pytest.mark.asyncio
    async def test_poll_empty_when_no_messages(self, mock_worker_config):
        """Poll should return empty list when no messages."""
        poller = MessagePoller(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        poller.client = AsyncMock()
        poller.client.get = AsyncMock(return_value=mock_response)

        messages = await poller.poll()
        assert messages == []

    @pytest.mark.asyncio
    async def test_poll_handles_error(self, mock_worker_config):
        """Poll should return empty list on errors."""
        poller = MessagePoller(mock_worker_config)
        poller.client = AsyncMock()
        poller.client.get = AsyncMock(side_effect=Exception("timeout"))

        messages = await poller.poll()
        assert messages == []

    @pytest.mark.asyncio
    async def test_poll_no_client(self, mock_worker_config):
        """Poll should return empty list when client is not initialized."""
        poller = MessagePoller(mock_worker_config)
        messages = await poller.poll()
        assert messages == []

    @pytest.mark.asyncio
    async def test_poll_non_200_returns_empty(self, mock_worker_config):
        """Non-200 status should return empty list."""
        poller = MessagePoller(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 500

        poller.client = AsyncMock()
        poller.client.get = AsyncMock(return_value=mock_response)

        messages = await poller.poll()
        assert messages == []

    @pytest.mark.asyncio
    async def test_poll_correct_url(self, mock_worker_config):
        """Poll should GET from /api/v1/sandboxes/{id}/messages."""
        poller = MessagePoller(mock_worker_config)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        poller.client = AsyncMock()
        poller.client.get = AsyncMock(return_value=mock_response)

        await poller.poll()

        url = poller.client.get.call_args[0][0]
        assert url == "http://localhost:8000/api/v1/sandboxes/sb-test-001/messages"


# ============================================================================
# Tests: check_git_status
# ============================================================================


class TestCheckGitStatus:
    """Tests for check_git_status git validation."""

    def test_clean_repo(self, tmp_git_workspace):
        """Clean repo should show is_clean=True."""
        result = check_git_status(str(tmp_git_workspace))
        assert result["is_clean"] is True
        assert result["branch_name"] is not None

    def test_dirty_repo(self, tmp_git_workspace):
        """Repo with uncommitted changes should show is_clean=False."""
        (tmp_git_workspace / "dirty.txt").write_text("uncommitted")
        result = check_git_status(str(tmp_git_workspace))
        assert result["is_clean"] is False
        assert "Uncommitted changes detected" in result["errors"]

    def test_branch_name_detected(self, tmp_git_workspace):
        """Current branch name should be detected."""
        result = check_git_status(str(tmp_git_workspace))
        # Default branch may be master or main depending on git config
        assert result["branch_name"] in ("main", "master")

    def test_non_git_directory(self, tmp_workspace):
        """Non-git directory should produce errors."""
        result = check_git_status(str(tmp_workspace))
        assert result["is_clean"] is False
        assert result["branch_name"] is None

    def test_result_structure(self, tmp_git_workspace):
        """Result should have all expected keys."""
        result = check_git_status(str(tmp_git_workspace))
        expected_keys = {
            "is_clean",
            "is_pushed",
            "has_pr",
            "branch_name",
            "status_output",
            "errors",
            "ci_status",
            "tests_passed",
            "pr_url",
            "pr_number",
            "files_changed",
        }
        assert expected_keys.issubset(result.keys())


# ============================================================================
# Tests: check_spec_output
# ============================================================================


class TestCheckSpecOutput:
    """Tests for check_spec_output spec file validation."""

    def test_no_omoi_dir(self, tmp_workspace):
        """Missing .omoi_os/ should fail validation."""
        result = check_spec_output(str(tmp_workspace))
        assert result["has_omoi_dir"] is False
        assert result["is_valid"] is False
        assert any(".omoi_os/ directory does not exist" in e for e in result["errors"])

    def test_empty_omoi_dir(self, tmp_workspace):
        """Empty .omoi_os/ should fail — no spec files found."""
        (tmp_workspace / ".omoi_os").mkdir()
        result = check_spec_output(str(tmp_workspace))
        assert result["has_omoi_dir"] is True
        assert result["is_valid"] is False
        assert any("No spec files found" in e for e in result["errors"])

    def test_valid_ticket_with_frontmatter(self, tmp_workspace):
        """Valid ticket file with proper frontmatter should pass."""
        omoi = tmp_workspace / ".omoi_os" / "tickets"
        omoi.mkdir(parents=True)
        (omoi / "TKT-001.md").write_text(
            "---\n"
            "id: TKT-001\n"
            "title: Fix auth\n"
            "status: backlog\n"
            "priority: HIGH\n"
            "---\n"
            "\n# Fix Authentication\n"
        )
        result = check_spec_output(str(tmp_workspace))
        assert result["has_omoi_dir"] is True
        assert result["is_valid"] is True
        assert len(result["files_found"]) == 1
        assert len(result["files_with_frontmatter"]) == 1
        assert len(result["files_missing_frontmatter"]) == 0

    def test_ticket_missing_required_field(self, tmp_workspace):
        """Ticket missing 'priority' should be flagged."""
        omoi = tmp_workspace / ".omoi_os" / "tickets"
        omoi.mkdir(parents=True)
        (omoi / "TKT-002.md").write_text(
            "---\n"
            "id: TKT-002\n"
            "title: Incomplete ticket\n"
            "status: backlog\n"
            "---\n"
            "\n# Missing priority\n"
        )
        result = check_spec_output(str(tmp_workspace))
        assert result["has_omoi_dir"] is True
        assert result["is_valid"] is False
        assert len(result["files_missing_frontmatter"]) == 1
        assert any("priority" in e for e in result["errors"])

    def test_file_without_frontmatter(self, tmp_workspace):
        """File without YAML frontmatter should fail."""
        omoi = tmp_workspace / ".omoi_os" / "tickets"
        omoi.mkdir(parents=True)
        (omoi / "TKT-003.md").write_text("# No frontmatter here\nJust text.\n")
        result = check_spec_output(str(tmp_workspace))
        assert result["is_valid"] is False
        assert any("Missing YAML frontmatter" in e for e in result["errors"])

    def test_valid_task_with_parent_ticket(self, tmp_workspace):
        """Task file with parent_ticket should pass validation."""
        omoi = tmp_workspace / ".omoi_os" / "tasks"
        omoi.mkdir(parents=True)
        (omoi / "TSK-001.md").write_text(
            "---\n"
            "id: TSK-001\n"
            "title: Implement login form\n"
            "status: todo\n"
            "parent_ticket: TKT-001\n"
            "---\n"
            "\n# Task Details\n"
        )
        result = check_spec_output(str(tmp_workspace))
        assert result["is_valid"] is True

    def test_multiple_spec_types(self, tmp_workspace):
        """Multiple spec directories with valid files should all pass."""
        omoi = tmp_workspace / ".omoi_os"

        # Create tickets
        tickets = omoi / "tickets"
        tickets.mkdir(parents=True)
        (tickets / "TKT-001.md").write_text(
            "---\nid: TKT-001\ntitle: T1\nstatus: backlog\npriority: HIGH\n---\n"
        )

        # Create tasks
        tasks = omoi / "tasks"
        tasks.mkdir(parents=True)
        (tasks / "TSK-001.md").write_text(
            "---\nid: TSK-001\ntitle: Task1\nstatus: todo\nparent_ticket: TKT-001\n---\n"
        )

        # Create designs
        designs = omoi / "designs"
        designs.mkdir(parents=True)
        (designs / "auth.md").write_text(
            "---\nid: DESIGN-AUTH-001\ntitle: Auth Design\nstatus: draft\n---\n"
        )

        result = check_spec_output(str(tmp_workspace))
        assert result["is_valid"] is True
        assert len(result["files_found"]) == 3
        assert len(result["files_with_frontmatter"]) == 3

    def test_mixed_valid_and_invalid(self, tmp_workspace):
        """Mix of valid and invalid files should mark invalid."""
        omoi = tmp_workspace / ".omoi_os" / "tickets"
        omoi.mkdir(parents=True)
        (omoi / "TKT-001.md").write_text(
            "---\nid: TKT-001\ntitle: Good\nstatus: backlog\npriority: HIGH\n---\n"
        )
        (omoi / "TKT-002.md").write_text("# Bad file, no frontmatter\n")

        result = check_spec_output(str(tmp_workspace))
        assert result["is_valid"] is False
        assert len(result["files_with_frontmatter"]) == 1
        assert len(result["files_missing_frontmatter"]) == 1


# ============================================================================
# Tests: find_dependency_files
# ============================================================================


class TestFindDependencyFiles:
    """Tests for find_dependency_files recursive search."""

    def test_empty_directory(self, tmp_workspace):
        """Empty directory should find no dependencies."""
        found = find_dependency_files(str(tmp_workspace))
        assert all(v is None for v in found.values())

    def test_finds_pyproject_toml(self, tmp_workspace):
        """Should find pyproject.toml at root."""
        (tmp_workspace / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        found = find_dependency_files(str(tmp_workspace))
        assert found["pyproject"] is not None
        assert "pyproject.toml" in found["pyproject"]

    def test_finds_requirements_txt(self, tmp_workspace):
        """Should find requirements.txt at root."""
        (tmp_workspace / "requirements.txt").write_text("flask==3.0\n")
        found = find_dependency_files(str(tmp_workspace))
        assert found["requirements"] is not None

    def test_finds_package_json(self, tmp_workspace):
        """Should find package.json at root."""
        (tmp_workspace / "package.json").write_text('{"name": "test"}')
        found = find_dependency_files(str(tmp_workspace))
        assert found["package_json"] is not None

    def test_finds_pnpm_lock(self, tmp_workspace):
        """Should find pnpm-lock.yaml."""
        (tmp_workspace / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n")
        found = find_dependency_files(str(tmp_workspace))
        assert found["pnpm_lock"] is not None

    def test_finds_uv_lock(self, tmp_workspace):
        """Should find uv.lock."""
        (tmp_workspace / "uv.lock").write_text("version = 1\n")
        found = find_dependency_files(str(tmp_workspace))
        assert found["uv_lock"] is not None

    def test_excludes_node_modules(self, tmp_workspace):
        """Should not find files inside node_modules."""
        nm = tmp_workspace / "node_modules" / "some-pkg"
        nm.mkdir(parents=True)
        (nm / "package.json").write_text('{"name": "dep"}')

        found = find_dependency_files(str(tmp_workspace))
        assert found["package_json"] is None

    def test_excludes_venv(self, tmp_workspace):
        """Should not find files inside .venv."""
        venv = tmp_workspace / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "requirements.txt").write_text("internal\n")

        found = find_dependency_files(str(tmp_workspace))
        assert found["requirements"] is None

    def test_prefers_shallowest(self, tmp_workspace):
        """Should prefer the shallowest matching file."""
        # Root level
        (tmp_workspace / "pyproject.toml").write_text("[project]\nname = 'root'\n")
        # Nested level
        sub = tmp_workspace / "subdir"
        sub.mkdir()
        (sub / "pyproject.toml").write_text("[project]\nname = 'nested'\n")

        found = find_dependency_files(str(tmp_workspace))
        assert found["pyproject"] is not None
        # Should pick root one (depth 0)
        assert Path(found["pyproject"]).parent == tmp_workspace

    def test_finds_nested_when_not_at_root(self, tmp_workspace):
        """Should find files in subdirectories when not at root."""
        backend = tmp_workspace / "backend"
        backend.mkdir()
        (backend / "pyproject.toml").write_text("[project]\nname = 'backend'\n")

        found = find_dependency_files(str(tmp_workspace))
        assert found["pyproject"] is not None
        assert "backend" in found["pyproject"]

    def test_returns_all_expected_keys(self, tmp_workspace):
        """Result should have all expected dependency file keys."""
        found = find_dependency_files(str(tmp_workspace))
        expected_keys = {
            "uv_lock",
            "poetry_lock",
            "pyproject",
            "requirements",
            "setup_py",
            "pnpm_lock",
            "yarn_lock",
            "npm_lock",
            "package_json",
        }
        assert set(found.keys()) == expected_keys


# ============================================================================
# Tests: install_project_dependencies
# ============================================================================


class TestInstallProjectDependencies:
    """Tests for install_project_dependencies automatic installation."""

    def test_no_dependency_files(self, tmp_workspace):
        """Empty workspace should produce no installations."""
        result = install_project_dependencies(str(tmp_workspace))
        assert result["python_installed"] is False
        assert result["node_installed"] is False
        assert result["python_manager"] is None
        assert result["node_manager"] is None
        assert "No dependency files detected" in result["summary"]

    @patch("subprocess.run")
    def test_uv_project_detected(self, mock_run, tmp_workspace):
        """UV project (uv.lock present) should call `uv sync`."""
        (tmp_workspace / "uv.lock").write_text("version = 1\n")
        (tmp_workspace / "pyproject.toml").write_text("[tool.uv]\n")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = install_project_dependencies(str(tmp_workspace))

        assert result["python_installed"] is True
        assert result["python_manager"] == "uv"
        # Verify uv sync was called
        uv_calls = [c for c in mock_run.call_args_list if c[0][0] == ["uv", "sync"]]
        assert len(uv_calls) >= 1

    @patch("subprocess.run")
    def test_pnpm_project_detected(self, mock_run, tmp_workspace):
        """pnpm project should call `pnpm install`."""
        (tmp_workspace / "package.json").write_text('{"name": "test"}')
        (tmp_workspace / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n")

        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = install_project_dependencies(str(tmp_workspace))

        assert result["node_installed"] is True
        assert result["node_manager"] == "pnpm"

    @patch("subprocess.run")
    def test_install_failure_recorded(self, mock_run, tmp_workspace):
        """Failed install should record errors."""
        (tmp_workspace / "requirements.txt").write_text("nonexistent-pkg\n")

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ERROR: Could not find package",
        )

        result = install_project_dependencies(str(tmp_workspace))

        assert result["python_installed"] is False
        assert len(result["errors"]) >= 1

    def test_result_structure(self, tmp_workspace):
        """Result should have all expected keys."""
        result = install_project_dependencies(str(tmp_workspace))
        expected_keys = {
            "python_installed",
            "python_manager",
            "python_dir",
            "node_installed",
            "node_manager",
            "node_dir",
            "errors",
            "summary",
        }
        assert expected_keys.issubset(result.keys())


# ============================================================================
# Tests: SandboxWorker (initialization only, no run)
# ============================================================================


class TestSandboxWorkerInit:
    """Tests for SandboxWorker initialization."""

    def test_init_sets_defaults(self, clean_env):
        from omoi_os.workers.claude_sandbox_worker import SandboxWorker

        env = {"ANTHROPIC_API_KEY": "test-key"}  # pragma: allowlist secret
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()
            worker = SandboxWorker(config)

        assert worker.running is False
        assert worker.turn_count == 0
        assert worker.reporter is None
        assert isinstance(worker.file_tracker, FileChangeTracker)
        assert isinstance(worker.iteration_state, IterationState)
        assert worker._should_stop is False
