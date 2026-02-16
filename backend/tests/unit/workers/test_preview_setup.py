"""Unit tests for PreviewSetupManager and preview system prompt injection.

Tests the worker-side preview support:
- PreviewSetupManager: env var parsing, frontend dir detection, notify calls
- WorkerConfig: system prompt injection when PREVIEW_ENABLED is set
"""

import json
import os
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from omoi_os.workers.claude_sandbox_worker import PreviewSetupManager, WorkerConfig

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config():
    """Create a minimal WorkerConfig mock."""
    config = MagicMock()
    config.cwd = "/workspace"
    config.callback_url = "https://api.example.com"
    config.sandbox_id = "sb-test-123"
    return config


@pytest.fixture
def tmp_frontend_dir(tmp_path):
    """Create a temporary directory with package.json containing a dev script."""
    pkg = {"name": "test-app", "scripts": {"dev": "vite"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    return str(tmp_path)


@pytest.fixture
def tmp_nested_frontend(tmp_path):
    """Create a temporary directory where frontend is in a subdirectory."""
    frontend_dir = tmp_path / "frontend"
    frontend_dir.mkdir()
    pkg = {"name": "nested-app", "scripts": {"dev": "next dev"}}
    (frontend_dir / "package.json").write_text(json.dumps(pkg))
    return str(tmp_path)


# ============================================================================
# Tests: PreviewSetupManager constructor
# ============================================================================


class TestPreviewSetupManagerInit:
    """Tests for PreviewSetupManager initialization from env vars."""

    def test_enabled_when_env_set(self, mock_config):
        """Manager should be enabled when PREVIEW_ENABLED=true."""
        with patch.dict(
            os.environ, {"PREVIEW_ENABLED": "true", "PREVIEW_PORT": "3000"}
        ):
            mgr = PreviewSetupManager(mock_config)
            assert mgr.enabled is True
            assert mgr.port == 3000

    def test_disabled_by_default(self, mock_config):
        """Manager should be disabled when PREVIEW_ENABLED is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure PREVIEW_ENABLED is not in env
            env = {k: v for k, v in os.environ.items() if k != "PREVIEW_ENABLED"}
            with patch.dict(os.environ, env, clear=True):
                mgr = PreviewSetupManager(mock_config)
                assert mgr.enabled is False

    def test_custom_port(self, mock_config):
        """Manager should use PREVIEW_PORT from env."""
        with patch.dict(
            os.environ, {"PREVIEW_ENABLED": "true", "PREVIEW_PORT": "8080"}
        ):
            mgr = PreviewSetupManager(mock_config)
            assert mgr.port == 8080

    def test_default_port_3000(self, mock_config):
        """Default port should be 3000 when PREVIEW_PORT not set."""
        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}, clear=False):
            env_without_port = {
                k: v for k, v in os.environ.items() if k != "PREVIEW_PORT"
            }
            with patch.dict(os.environ, env_without_port, clear=True):
                mgr = PreviewSetupManager(mock_config)
                assert mgr.port == 3000

    def test_case_insensitive_enabled(self, mock_config):
        """PREVIEW_ENABLED should be case-insensitive."""
        with patch.dict(os.environ, {"PREVIEW_ENABLED": "TRUE"}):
            mgr = PreviewSetupManager(mock_config)
            assert mgr.enabled is True


# ============================================================================
# Tests: _find_frontend_dir
# ============================================================================


class TestFindFrontendDir:
    """Tests for PreviewSetupManager._find_frontend_dir."""

    def test_finds_package_json_in_base(self, mock_config, tmp_frontend_dir):
        """Should find frontend dir when package.json is in the base directory."""
        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}):
            mgr = PreviewSetupManager(mock_config)
            result = mgr._find_frontend_dir(tmp_frontend_dir)
            assert result == tmp_frontend_dir

    def test_finds_nested_frontend_dir(self, mock_config, tmp_nested_frontend):
        """Should find frontend dir in /frontend subdirectory."""
        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}):
            mgr = PreviewSetupManager(mock_config)
            result = mgr._find_frontend_dir(tmp_nested_frontend)
            assert result == str(Path(tmp_nested_frontend) / "frontend")

    def test_returns_none_when_no_package_json(self, mock_config, tmp_path):
        """Should return None when no package.json exists."""
        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}):
            mgr = PreviewSetupManager(mock_config)
            result = mgr._find_frontend_dir(str(tmp_path))
            assert result is None

    def test_ignores_package_json_without_dev_script(self, mock_config, tmp_path):
        """Should ignore package.json that lacks a dev script."""
        pkg = {"name": "lib-only", "scripts": {"build": "tsc"}}
        (tmp_path / "package.json").write_text(json.dumps(pkg))

        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}):
            mgr = PreviewSetupManager(mock_config)
            result = mgr._find_frontend_dir(str(tmp_path))
            assert result is None

    def test_handles_malformed_package_json(self, mock_config, tmp_path):
        """Should gracefully skip malformed package.json."""
        (tmp_path / "package.json").write_text("not valid json {{{")

        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}):
            mgr = PreviewSetupManager(mock_config)
            result = mgr._find_frontend_dir(str(tmp_path))
            assert result is None


# ============================================================================
# Tests: _notify
# ============================================================================


class TestPreviewNotify:
    """Tests for PreviewSetupManager._notify HTTP calls."""

    @pytest.mark.asyncio
    async def test_notify_posts_to_correct_url(self, mock_config):
        """Notify should POST to /api/v1/preview/notify on the callback URL."""
        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}):
            mgr = PreviewSetupManager(mock_config)

            mock_response = MagicMock()
            mock_response.status_code = 200

            with patch("httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                MockClient.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

                await mgr._notify("starting")

                mock_client_instance.post.assert_awaited_once()
                call_args = mock_client_instance.post.call_args
                assert (
                    call_args[0][0] == "https://api.example.com/api/v1/preview/notify"
                )
                assert call_args[1]["json"]["sandbox_id"] == "sb-test-123"
                assert call_args[1]["json"]["status"] == "starting"

    @pytest.mark.asyncio
    async def test_notify_includes_error_message(self, mock_config):
        """Notify with error_message should include it in the payload."""
        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}):
            mgr = PreviewSetupManager(mock_config)

            mock_response = MagicMock()
            mock_response.status_code = 200

            with patch("httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.post = AsyncMock(return_value=mock_response)
                MockClient.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

                await mgr._notify("failed", error_message="Server crashed")

                payload = mock_client_instance.post.call_args[1]["json"]
                assert payload["status"] == "failed"
                assert payload["error_message"] == "Server crashed"

    @pytest.mark.asyncio
    async def test_notify_handles_network_error(self, mock_config):
        """Notify should not raise on network errors (best-effort)."""
        with patch.dict(os.environ, {"PREVIEW_ENABLED": "true"}):
            mgr = PreviewSetupManager(mock_config)

            with patch("httpx.AsyncClient") as MockClient:
                mock_client_instance = AsyncMock()
                mock_client_instance.post = AsyncMock(
                    side_effect=Exception("Connection refused")
                )
                MockClient.return_value.__aenter__ = AsyncMock(
                    return_value=mock_client_instance
                )
                MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

                # Should not raise
                await mgr._notify("ready")


# ============================================================================
# Tests: System prompt injection
# ============================================================================


class TestSystemPromptPreviewInjection:
    """Tests for preview instructions being injected into the system prompt."""

    def test_preview_instructions_injected_when_enabled(self):
        """WorkerConfig should include preview instructions when PREVIEW_ENABLED=true."""
        env = {
            "PREVIEW_ENABLED": "true",
            "PREVIEW_PORT": "3000",
            "SANDBOX_ID": "sb-test",
            "CALLBACK_URL": "http://localhost:8000",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
            "TASK_ID": "task-123",
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()
            # The system_prompt should be a dict with "append" key containing preview text
            if isinstance(config.system_prompt, dict):
                append_text = config.system_prompt.get("append", "")
            else:
                append_text = config.system_prompt or ""

            assert "Live Preview" in append_text
            assert "port 3000" in append_text
            assert "dev server" in append_text.lower() or "dev server" in append_text

    def test_preview_instructions_not_injected_when_disabled(self):
        """WorkerConfig should NOT include preview instructions when PREVIEW_ENABLED is not set."""
        env = {
            "SANDBOX_ID": "sb-test",
            "CALLBACK_URL": "http://localhost:8000",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
            "TASK_ID": "task-123",
        }
        # Remove PREVIEW_ENABLED from env
        cleaned_env = {k: v for k, v in os.environ.items() if k != "PREVIEW_ENABLED"}
        cleaned_env.update(env)
        with patch.dict(os.environ, cleaned_env, clear=True):
            config = WorkerConfig()
            if isinstance(config.system_prompt, dict):
                append_text = config.system_prompt.get("append", "")
            elif config.system_prompt is None:
                append_text = ""
            else:
                append_text = config.system_prompt

            assert "Live Preview" not in append_text

    def test_preview_uses_custom_port(self):
        """Preview instructions should use the configured port number."""
        env = {
            "PREVIEW_ENABLED": "true",
            "PREVIEW_PORT": "8080",
            "SANDBOX_ID": "sb-test",
            "CALLBACK_URL": "http://localhost:8000",
            "ANTHROPIC_API_KEY": "test-key",  # pragma: allowlist secret
            "TASK_ID": "task-123",
        }
        with patch.dict(os.environ, env, clear=False):
            config = WorkerConfig()
            if isinstance(config.system_prompt, dict):
                append_text = config.system_prompt.get("append", "")
            else:
                append_text = config.system_prompt or ""

            assert "port 8080" in append_text
