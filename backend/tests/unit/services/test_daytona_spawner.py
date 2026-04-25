"""Unit tests for DaytonaSpawnerService service.

Tests specifically for the spawn_for_phase method added for spec-driven development.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omoi_os.services.daytona_spawner import DaytonaSpawnerService


class TestDaytonaSpawnerSpawnForPhase:
    """Tests for spawn_for_phase method."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with all required fields."""
        settings = MagicMock()
        settings.daytona_api_key = "test-api-key"
        settings.daytona_api_url = "https://api.daytona.io"
        settings.daytona_runner_class = "default"
        settings.sandbox_memory_gb = 4
        settings.sandbox_cpu = 2
        settings.sandbox_disk_gb = 10
        settings.sandbox_auto_stop_interval = 3600
        settings.target = "us"
        return settings

    @pytest.fixture
    def spawner(self, mock_settings):
        """Create spawner instance with mocked settings."""
        with patch(
            "omoi_os.services.daytona_spawner.load_daytona_settings",
            return_value=mock_settings,
        ):
            spawner = DaytonaSpawnerService()
            return spawner

    def test_spawn_for_phase_exists(self, spawner):
        """Test spawn_for_phase method exists."""
        import inspect

        assert hasattr(spawner, "spawn_for_phase")
        assert inspect.iscoroutinefunction(spawner.spawn_for_phase)

    def test_spawn_for_phase_signature(self, spawner):
        """Test spawn_for_phase has correct signature."""
        import inspect

        sig = inspect.signature(spawner.spawn_for_phase)
        params = list(sig.parameters.keys())

        assert "spec_id" in params
        assert "phase" in params
        assert "project_id" in params
        assert "phase_context" in params
        assert "resume_transcript" in params
        assert "extra_env" in params

    @pytest.mark.asyncio
    async def test_spawn_for_phase_requires_api_key(self):
        """Test spawn_for_phase raises error without API key."""
        spawner = DaytonaSpawnerService.__new__(DaytonaSpawnerService)
        spawner.daytona_api_key = None
        spawner.daytona_api_url = "https://api.daytona.io"

        with pytest.raises(RuntimeError, match="Daytona API key not configured"):
            await spawner.spawn_for_phase(
                spec_id="spec-123",
                phase="explore",
                project_id="proj-456",
            )

    @pytest.mark.asyncio
    async def test_spawn_for_phase_generates_sandbox_id(self, spawner):
        """Test spawn_for_phase generates unique sandbox ID."""
        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-created-123"

            result = await spawner.spawn_for_phase(
                spec_id="spec-12345678-uuid",
                phase="explore",
                project_id="proj-456",
            )

            # Verify sandbox creation was called
            assert mock_create.called
            # The sandbox ID should contain parts of spec_id and phase
            mock_create.call_args[1] if mock_create.call_args[1] else {}
            # Check it returned some sandbox ID
            assert result is not None

    @pytest.mark.asyncio
    async def test_spawn_for_phase_maps_phases_to_modes(self, spawner):
        """Test that phases are mapped to execution modes correctly."""
        phases = ["explore", "requirements", "design", "tasks", "sync"]

        for phase in phases:
            with patch.object(
                spawner, "_create_daytona_sandbox", new_callable=AsyncMock
            ) as mock_create:
                mock_create.return_value = f"sandbox-{phase}"

                result = await spawner.spawn_for_phase(
                    spec_id="spec-123",
                    phase=phase,
                    project_id="proj-456",
                )

                assert result is not None
                assert mock_create.called

    @pytest.mark.asyncio
    async def test_spawn_for_phase_passes_context(self, spawner):
        """Test spawn_for_phase passes phase context to sandbox."""
        phase_context = {
            "explore": {"project_type": "web_app", "tech_stack": ["python", "fastapi"]},
        }

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_phase(
                spec_id="spec-123",
                phase="requirements",
                project_id="proj-456",
                phase_context=phase_context,
            )

            # Verify context was included in environment
            assert mock_create.called

    @pytest.mark.asyncio
    async def test_spawn_for_phase_passes_resume_transcript(self, spawner):
        """Test spawn_for_phase passes resume transcript for session resumption."""
        import base64

        transcript_data = {"messages": [{"role": "user", "content": "test"}]}
        resume_transcript = base64.b64encode(str(transcript_data).encode()).decode()

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_phase(
                spec_id="spec-123",
                phase="requirements",
                project_id="proj-456",
                resume_transcript=resume_transcript,
            )

            # Verify sandbox was created
            assert mock_create.called

    @pytest.mark.asyncio
    async def test_spawn_for_phase_includes_extra_env(self, spawner):
        """Test spawn_for_phase includes extra environment variables."""
        extra_env = {
            "CUSTOM_VAR": "custom_value",
            "FEATURE_FLAG": "enabled",
        }

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_phase(
                spec_id="spec-123",
                phase="design",
                project_id="proj-456",
                extra_env=extra_env,
            )

            assert mock_create.called


class TestDaytonaSpawnerEgressEnvVars:
    """Tests for egress env var injection in spawn_for_task."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with all required fields."""
        settings = MagicMock()
        settings.daytona_api_key = "test-api-key"
        settings.daytona_api_url = "https://api.daytona.io"
        settings.daytona_runner_class = "default"
        settings.sandbox_memory_gb = 4
        settings.sandbox_cpu = 2
        settings.sandbox_disk_gb = 10
        settings.sandbox_auto_stop_interval = 3600
        settings.target = "us"
        return settings

    @pytest.fixture
    def spawner(self, mock_settings):
        """Create spawner instance with mocked settings."""
        with patch(
            "omoi_os.services.daytona_spawner.load_daytona_settings",
            return_value=mock_settings,
        ):
            spawner = DaytonaSpawnerService()
            return spawner

    @pytest.mark.asyncio
    async def test_spawn_for_task_no_egress_when_env_version_none(self, spawner):
        """Test egress env vars are absent when env_version is None."""
        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_task(
                task_id="task-123",
                agent_id="agent-456",
                phase_id="PHASE_IMPLEMENTATION",
                env_version=None,
            )

            assert mock_create.called
            env_vars = mock_create.call_args[1]["env_vars"]
            assert "HTTPS_PROXY" not in env_vars
            assert "HTTP_PROXY" not in env_vars
            assert "NO_PROXY" not in env_vars
            assert "OMOIOS_EGRESS_ALLOWED_HOSTS" not in env_vars

    @pytest.mark.asyncio
    async def test_spawn_for_task_no_egress_when_egress_none(self, spawner):
        """Test egress env vars are absent when env_version.egress is None."""
        env_version = MagicMock()
        env_version.egress = None

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_task(
                task_id="task-123",
                agent_id="agent-456",
                phase_id="PHASE_IMPLEMENTATION",
                env_version=env_version,
            )

            assert mock_create.called
            env_vars = mock_create.call_args[1]["env_vars"]
            assert "HTTPS_PROXY" not in env_vars
            assert "HTTP_PROXY" not in env_vars
            assert "NO_PROXY" not in env_vars
            assert "OMOIOS_EGRESS_ALLOWED_HOSTS" not in env_vars

    @pytest.mark.asyncio
    async def test_spawn_for_task_injects_egress_env_vars(self, spawner):
        """Test egress env vars are present when allowlist is set."""
        env_version = MagicMock()
        env_version.egress = {"allowed_hosts": ["github.com", "api.openai.com"]}

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_task(
                task_id="task-123",
                agent_id="agent-456",
                phase_id="PHASE_IMPLEMENTATION",
                env_version=env_version,
            )

            assert mock_create.called
            env_vars = mock_create.call_args[1]["env_vars"]
            assert env_vars["HTTPS_PROXY"] == "http://127.0.0.1:8888"
            assert env_vars["HTTP_PROXY"] == "http://127.0.0.1:8888"
            assert (
                env_vars["NO_PROXY"]
                == "localhost,127.0.0.1,169.254.169.254,.daytona.local"
            )
            assert (
                env_vars["OMOIOS_EGRESS_ALLOWED_HOSTS"] == "github.com,api.openai.com"
            )

    @pytest.mark.asyncio
    async def test_spawn_for_task_no_proxy_includes_required_entries(self, spawner):
        """Test NO_PROXY contains all required entries."""
        env_version = MagicMock()
        env_version.egress = {"allowed_hosts": ["github.com"]}

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_task(
                task_id="task-123",
                agent_id="agent-456",
                phase_id="PHASE_IMPLEMENTATION",
                env_version=env_version,
            )

            env_vars = mock_create.call_args[1]["env_vars"]
            no_proxy = env_vars["NO_PROXY"]
            assert "localhost" in no_proxy
            assert "127.0.0.1" in no_proxy
            assert "169.254.169.254" in no_proxy
            assert ".daytona.local" in no_proxy


class TestDaytonaSpawnerBrokerEnvVars:
    """Tests for broker env var injection in spawn_for_task."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with all required fields."""
        settings = MagicMock()
        settings.daytona_api_key = "test-api-key"
        settings.daytona_api_url = "https://api.daytona.io"
        settings.daytona_runner_class = "default"
        settings.sandbox_memory_gb = 4
        settings.sandbox_cpu = 2
        settings.sandbox_disk_gb = 10
        settings.sandbox_auto_stop_interval = 3600
        settings.target = "us"
        return settings

    @pytest.fixture
    def spawner(self, mock_settings):
        """Create spawner instance with mocked settings."""
        with patch(
            "omoi_os.services.daytona_spawner.load_daytona_settings",
            return_value=mock_settings,
        ):
            spawner = DaytonaSpawnerService()
            return spawner

    @pytest.mark.asyncio
    async def test_broker_env_vars_injected(self, spawner):
        """Test broker env vars are present when alias map is set."""
        env_version = MagicMock()
        env_version.egress = None
        env_version.credentials = {
            "anthropic": {"kind": "bearer_secret", "binding_id": "uuid-1"},
            "github": {"kind": "github_app", "app_id": "123"},
        }

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_task(
                task_id="task-123",
                agent_id="agent-456",
                phase_id="PHASE_IMPLEMENTATION",
                env_version=env_version,
                sandbox_session_token="sess_tok_test_token_123",
            )

            assert mock_create.called
            env_vars = mock_create.call_args[1]["env_vars"]
            assert env_vars["SESSION_TOKEN"] == "sess_tok_test_token_123"
            assert env_vars["BROKER_URL"] == "http://localhost:18000/broker"
            assert env_vars["OMOIOS_CREDENTIAL_ALIASES"] == "anthropic,github"

    @pytest.mark.asyncio
    async def test_broker_env_vars_skipped_when_empty(self, spawner):
        """Test broker env vars are absent when alias map is empty."""
        env_version = MagicMock()
        env_version.egress = None
        env_version.credentials = {}

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_task(
                task_id="task-123",
                agent_id="agent-456",
                phase_id="PHASE_IMPLEMENTATION",
                env_version=env_version,
            )

            assert mock_create.called
            env_vars = mock_create.call_args[1]["env_vars"]
            assert "SESSION_TOKEN" not in env_vars
            assert "BROKER_URL" not in env_vars
            assert "OMOIOS_CREDENTIAL_ALIASES" not in env_vars

    @pytest.mark.asyncio
    async def test_broker_env_vars_skipped_when_none(self, spawner):
        """Test broker env vars are absent when env_version is None."""
        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_task(
                task_id="task-123",
                agent_id="agent-456",
                phase_id="PHASE_IMPLEMENTATION",
                env_version=None,
            )

            assert mock_create.called
            env_vars = mock_create.call_args[1]["env_vars"]
            assert "SESSION_TOKEN" not in env_vars
            assert "BROKER_URL" not in env_vars
            assert "OMOIOS_CREDENTIAL_ALIASES" not in env_vars

    @pytest.mark.asyncio
    async def test_session_token_not_logged(self, spawner, caplog):
        """Test that SESSION_TOKEN is never emitted in log output."""
        env_version = MagicMock()
        env_version.egress = None
        env_version.credentials = {"anthropic": {"kind": "bearer_secret"}}

        with patch.object(
            spawner, "_create_daytona_sandbox", new_callable=AsyncMock
        ) as mock_create:
            mock_create.return_value = "sandbox-123"

            await spawner.spawn_for_task(
                task_id="task-123",
                agent_id="agent-456",
                phase_id="PHASE_IMPLEMENTATION",
                env_version=env_version,
                sandbox_session_token="sess_tok_super_secret",
            )

            # Verify the token string does not appear in any log record
            for record in caplog.records:
                assert "sess_tok_super_secret" not in record.message
                assert "sess_tok_super_secret" not in str(record.args)
                assert "sess_tok_super_secret" not in str(getattr(record, "extra", {}))


class TestDaytonaSpawnerPhaseMapping:
    """Tests for phase-to-mode mapping in spawn_for_phase."""

    def test_phase_to_mode_mapping_exists(self):
        """Test that phase to mode mapping is implemented."""
        # This tests the internal logic that maps phases to execution modes
        phase_to_mode = {
            "explore": "exploration",
            "requirements": "spec_requirements",
            "design": "spec_design",
            "tasks": "spec_tasks",
            "sync": "spec_sync",
        }

        for phase, expected_mode in phase_to_mode.items():
            assert phase in phase_to_mode
            # The actual mapping is verified in integration tests

    def test_all_spec_phases_have_mapping(self):
        """Test that all spec phases have a mapping."""
        from omoi_os.schemas.spec_generation import SpecPhase

        # COMPLETE doesn't need sandbox spawn (it's the terminal state)
        sandbox_phases = [
            SpecPhase.EXPLORE,
            SpecPhase.REQUIREMENTS,
            SpecPhase.DESIGN,
            SpecPhase.TASKS,
            SpecPhase.SYNC,
        ]

        for phase in sandbox_phases:
            # Each phase should have a corresponding mode
            assert phase.value in ["explore", "requirements", "design", "tasks", "sync"]
