"""Tests for `services.modal_sandboxed_agent` and the chat-responder
provider-aware dispatch path.

The integration test that actually drives a Modal sandbox lives in
`scripts/modal_sandbox_smoke.py` and is gated behind real Modal creds.
This module covers the parts that don't need network: dispatch routing,
stdout parsing, and config rendering.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omoi_os.services import modal_sandboxed_agent as msa


# ─── _extract_opencode_reply ─────────────────────────────────────────────────


class TestExtractOpencodeReply:
    def test_empty(self) -> None:
        assert msa._extract_opencode_reply("") == ""

    def test_strips_leading_banner(self) -> None:
        out = "> opencode v1.2.3\n\nhello world\n"
        assert msa._extract_opencode_reply(out) == "hello world"

    def test_keeps_blank_lines_in_body(self) -> None:
        out = "> opencode v1.2.3\nfirst para\n\nsecond para\n"
        assert msa._extract_opencode_reply(out) == "first para\n\nsecond para"

    def test_no_banner_passthrough(self) -> None:
        assert msa._extract_opencode_reply("just text\n") == "just text"


# ─── is_enabled ──────────────────────────────────────────────────────────────


class TestIsEnabled:
    @patch("omoi_os.config.get_app_settings")
    def test_off_when_feature_flag_disabled(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.feature_flags.sandboxed_agent_enabled = False
        mock_settings.return_value.sandbox.provider = "modal"
        assert msa.is_enabled() is False

    @patch("omoi_os.config.get_app_settings")
    def test_off_when_provider_is_daytona(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.feature_flags.sandboxed_agent_enabled = True
        mock_settings.return_value.sandbox.provider = "daytona"
        assert msa.is_enabled() is False

    @patch("omoi_os.config.get_app_settings")
    def test_on_when_flag_and_provider_modal(self, mock_settings: MagicMock) -> None:
        mock_settings.return_value.feature_flags.sandboxed_agent_enabled = True
        mock_settings.return_value.sandbox.provider = "modal"
        assert msa.is_enabled() is True

    @patch("omoi_os.config.get_app_settings", side_effect=RuntimeError("boom"))
    def test_off_on_settings_error(self, _mock_settings: MagicMock) -> None:
        assert msa.is_enabled() is False


# ─── ModalSandboxedAgent.prompt ──────────────────────────────────────────────


class TestModalSandboxedAgentPrompt:
    @pytest.mark.asyncio
    async def test_returns_extracted_reply_on_success(self) -> None:
        spawner = MagicMock()
        spawner.exec = AsyncMock(
            return_value={
                "stdout": "> opencode v1.0\nhello back\n",
                "stderr": "",
                "exit_code": 0,
            }
        )
        agent = msa.ModalSandboxedAgent(
            omoios_session_id="sess-1",
            sandbox_id="sb-abc",
            spawner=spawner,
            provider="fireworks-ai",
            model="x",
            spawned_at=0.0,
        )
        reply = await agent.prompt("hi")
        assert reply == "hello back"
        # Ensure we used the pinned opencode binary path + < /dev/null + timeout
        cmd = spawner.exec.call_args[0]
        assert cmd[0] == "sb-abc"
        assert cmd[1] == "bash"
        assert cmd[2] == "-lc"
        joined = cmd[3]
        assert "/root/.opencode/bin/opencode run" in joined
        assert "< /dev/null" in joined
        assert "timeout " in joined
        # The user prompt lands as the final arg before stdin redirection.
        # shlex.quote("hi") is just "hi" (no escaping needed for simple
        # words); the adversarial-input test below covers the escaping path.
        assert "hi < /dev/null" in joined

    @pytest.mark.asyncio
    async def test_returns_empty_on_nonzero_exit(self) -> None:
        spawner = MagicMock()
        spawner.exec = AsyncMock(
            return_value={"stdout": "", "stderr": "boom", "exit_code": 124}
        )
        agent = msa.ModalSandboxedAgent(
            omoios_session_id="sess-1",
            sandbox_id="sb-abc",
            spawner=spawner,
            provider="fireworks-ai",
            model="x",
            spawned_at=0.0,
        )
        assert await agent.prompt("hi") == ""

    @pytest.mark.asyncio
    async def test_prompt_with_shell_metachars_is_quoted(self) -> None:
        """An adversarial prompt with single quotes / `;` / `$()` must
        not break out of the bash -lc invocation."""
        spawner = MagicMock()
        spawner.exec = AsyncMock(
            return_value={"stdout": "ok", "stderr": "", "exit_code": 0}
        )
        agent = msa.ModalSandboxedAgent(
            omoios_session_id="sess-1",
            sandbox_id="sb-abc",
            spawner=spawner,
            provider="fireworks-ai",
            model="x",
            spawned_at=0.0,
        )
        adversarial = "hi'; rm -rf / #"
        await agent.prompt(adversarial)
        joined = spawner.exec.call_args[0][3]
        # Validate that shlex.quote has wrapped the dangerous payload.
        # Anything else means the shell would have parsed it.
        import shlex

        assert shlex.quote(adversarial) in joined


# ─── chat_responder dispatch ─────────────────────────────────────────────────


class TestChatResponderDispatch:
    @pytest.mark.asyncio
    @patch("omoi_os.config.get_app_settings")
    async def test_returns_empty_when_flag_off(self, mock_settings: MagicMock) -> None:
        from omoi_os.services.chat_responder import _dispatch_to_sandboxed_agent

        mock_settings.return_value.feature_flags.sandboxed_agent_enabled = False
        mock_settings.return_value.sandbox.provider = "modal"
        assert await _dispatch_to_sandboxed_agent("sess-1", "hi") == ""

    @pytest.mark.asyncio
    @patch("omoi_os.config.get_app_settings")
    async def test_routes_to_modal_when_provider_modal(
        self, mock_settings: MagicMock
    ) -> None:
        from omoi_os.services.chat_responder import _dispatch_to_sandboxed_agent

        mock_settings.return_value.feature_flags.sandboxed_agent_enabled = True
        mock_settings.return_value.sandbox.provider = "modal"
        fake_agent = MagicMock()
        fake_agent.prompt = AsyncMock(return_value="modal-reply")
        with patch.object(msa, "get_or_spawn", AsyncMock(return_value=fake_agent)):
            reply = await _dispatch_to_sandboxed_agent("sess-1", "hi")
        assert reply == "modal-reply"
        fake_agent.prompt.assert_awaited_once_with("hi")

    @pytest.mark.asyncio
    @patch("omoi_os.config.get_app_settings")
    async def test_routes_to_daytona_when_provider_daytona(
        self, mock_settings: MagicMock
    ) -> None:
        from omoi_os.services import sandboxed_agent as daytona
        from omoi_os.services.chat_responder import _dispatch_to_sandboxed_agent

        mock_settings.return_value.feature_flags.sandboxed_agent_enabled = True
        mock_settings.return_value.sandbox.provider = "daytona"
        fake_agent = MagicMock()
        fake_agent.prompt = AsyncMock(return_value="daytona-reply")
        with patch.object(daytona, "get_or_spawn", AsyncMock(return_value=fake_agent)):
            reply = await _dispatch_to_sandboxed_agent("sess-1", "hi")
        assert reply == "daytona-reply"
        fake_agent.prompt.assert_awaited_once_with("hi")

    @pytest.mark.asyncio
    @patch("omoi_os.config.get_app_settings")
    async def test_returns_empty_for_unknown_provider(
        self, mock_settings: MagicMock
    ) -> None:
        from omoi_os.services.chat_responder import _dispatch_to_sandboxed_agent

        mock_settings.return_value.feature_flags.sandboxed_agent_enabled = True
        mock_settings.return_value.sandbox.provider = "local"  # not wired
        assert await _dispatch_to_sandboxed_agent("sess-1", "hi") == ""
