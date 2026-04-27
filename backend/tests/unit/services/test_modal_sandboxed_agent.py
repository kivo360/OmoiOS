"""Tests for `services.modal_sandboxed_agent` and the chat-responder
provider-aware dispatch path.

The integration test that actually drives a Modal sandbox lives in
`backend/tests/integration/test_modal_sandboxed_agent_live.py` and is
gated behind `RUN_LIVE_MODAL=1`. This module covers the parts that
don't need network: dispatch routing, event filtering, text assembly,
prompt streaming behavior, and rehydration shape.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from omoi_os.services import modal_sandboxed_agent as msa


# ─── _event_matches_session ──────────────────────────────────────────────────


class TestEventMatchesSession:
    def test_top_level_session_id_match(self) -> None:
        evt = {"type": "session.idle", "properties": {"sessionID": "ses_x"}}
        assert msa._event_matches_session(evt, "ses_x") is True

    def test_part_nested_session_id_match(self) -> None:
        evt = {
            "type": "message.part.updated",
            "properties": {"part": {"sessionID": "ses_x", "type": "text"}},
        }
        assert msa._event_matches_session(evt, "ses_x") is True

    def test_info_nested_session_id_match(self) -> None:
        evt = {
            "type": "session.updated",
            "properties": {"info": {"id": "ses_x", "title": "anything"}},
        }
        assert msa._event_matches_session(evt, "ses_x") is True

    def test_no_match(self) -> None:
        evt = {"type": "server.connected", "properties": {}}
        assert msa._event_matches_session(evt, "ses_x") is False

    def test_different_session_no_match(self) -> None:
        evt = {"type": "session.idle", "properties": {"sessionID": "ses_other"}}
        assert msa._event_matches_session(evt, "ses_x") is False


# ─── _assemble_text ──────────────────────────────────────────────────────────


class TestAssembleText:
    def test_empty(self) -> None:
        assert msa._assemble_text([]) == ""

    def test_text_parts_joined(self) -> None:
        parts = [
            {"type": "step-start"},
            {"type": "reasoning", "text": "thinking…"},
            {"type": "text", "text": "hello"},
            {"type": "text", "text": "world"},
            {"type": "step-finish"},
        ]
        assert msa._assemble_text(parts) == "hello\nworld"

    def test_skips_non_text_parts(self) -> None:
        parts = [
            {"type": "tool", "tool": "bash", "state": {}},
            {"type": "text", "text": "ok"},
        ]
        assert msa._assemble_text(parts) == "ok"


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


# ─── ModalSandboxedAgent.prompt — streaming + assembly ──────────────────────


def _agent(opencode_session_id: str = "ses_x") -> msa.ModalSandboxedAgent:
    return msa.ModalSandboxedAgent(
        omoios_session_id="omoios-1",
        sandbox_id="sb-abc",
        spawner=MagicMock(),
        tunnel_url="https://fake.tunnel",
        opencode_session_id=opencode_session_id,
        provider="fireworks-ai",
        model="kimi",
        spawned_at=0.0,
    )


class _FakeSSESource:
    def __init__(self, events: list[dict]) -> None:
        self._events = events

    async def __aenter__(self) -> "_FakeSSESource":
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def aiter_sse(self):
        for evt in self._events:
            import json

            yield MagicMock(data=json.dumps(evt))


class TestModalSandboxedAgentPrompt:
    @pytest.mark.asyncio
    async def test_returns_assembled_text_and_invokes_callback(self) -> None:
        sid = "ses_x"
        events = [
            {
                "type": "message.part.updated",
                "properties": {
                    "part": {
                        "id": "prt-1",
                        "type": "text",
                        "text": "PONG",
                        "sessionID": sid,
                        "messageID": "msg-1",
                    }
                },
            },
            {"type": "session.idle", "properties": {"sessionID": sid}},
        ]
        final_body = {
            "info": {"id": "msg-1", "sessionID": sid, "role": "assistant"},
            "parts": [{"type": "text", "text": "PONG", "messageID": "msg-1"}],
        }

        seen: list[tuple[str, dict]] = []

        async def cb(et: str, props: dict) -> None:
            seen.append((et, props))

        agent = _agent(sid)

        async def fake_post(url, **kwargs):  # noqa: ANN001
            return httpx.Response(
                200, json=final_body, request=httpx.Request("POST", url)
            )

        with (
            patch.object(msa, "aconnect_sse", lambda *a, **kw: _FakeSSESource(events)),
            patch.object(httpx.AsyncClient, "post", AsyncMock(side_effect=fake_post)),
        ):
            text = await agent.prompt("hi", on_part=cb)

        assert text == "PONG"
        assert any(et == "message.part.updated" for et, _ in seen)
        assert any(et == "session.idle" for et, _ in seen)

    @pytest.mark.asyncio
    async def test_back_compat_no_callback(self) -> None:
        sid = "ses_x"
        events = [{"type": "session.idle", "properties": {"sessionID": sid}}]
        final_body = {
            "info": {"id": "msg-1", "sessionID": sid, "role": "assistant"},
            "parts": [{"type": "text", "text": "hi"}],
        }
        agent = _agent(sid)

        async def fake_post(url, **kwargs):  # noqa: ANN001
            return httpx.Response(
                200, json=final_body, request=httpx.Request("POST", url)
            )

        with (
            patch.object(msa, "aconnect_sse", lambda *a, **kw: _FakeSSESource(events)),
            patch.object(httpx.AsyncClient, "post", AsyncMock(side_effect=fake_post)),
        ):
            text = await agent.prompt("hi")  # no on_part — must still work
        assert text == "hi"

    @pytest.mark.asyncio
    async def test_empty_string_when_post_raises(self) -> None:
        sid = "ses_x"
        agent = _agent(sid)

        async def boom(*a, **kw):  # noqa: ANN001
            raise httpx.HTTPError("boom")

        with (
            patch.object(msa, "aconnect_sse", lambda *a, **kw: _FakeSSESource([])),
            patch.object(httpx.AsyncClient, "post", AsyncMock(side_effect=boom)),
        ):
            text = await agent.prompt("hi")
        assert text == ""


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
        # The caller may pass on_part now — assert prompt was called with the
        # text positionally, regardless of kwargs.
        assert fake_agent.prompt.await_args.args == ("hi",)

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


# ─── cross-replica rehydration ───────────────────────────────────────────────


def _live_state(**overrides: object) -> dict:
    import time as _time

    base = {
        "runtime": "opencode-modal",
        "status": "live",
        "sandbox_id": "sb-1",
        "modal_object_id": "modal-abc",
        "tunnel_url": "https://t.modal.host",
        "opencode_session_id": "ses_persisted",
        "provider": "fireworks-ai",
        "model": "kimi",
        "spawned_at": _time.time(),
    }
    base.update(overrides)
    return base


class TestRehydrateAgent:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_state(self) -> None:
        with patch.object(msa, "_load_runtime_state", AsyncMock(return_value=None)):
            assert await msa._rehydrate_agent("sess-1") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_runtime_is_daytona(self) -> None:
        state = _live_state(runtime="opencode")
        with patch.object(msa, "_load_runtime_state", AsyncMock(return_value=state)):
            assert await msa._rehydrate_agent("sess-1") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_status_closed(self) -> None:
        state = _live_state(status="closed")
        with patch.object(msa, "_load_runtime_state", AsyncMock(return_value=state)):
            assert await msa._rehydrate_agent("sess-1") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_too_old(self) -> None:
        state = _live_state(spawned_at=1.0)  # epoch — far past 6h cutoff
        with patch.object(msa, "_load_runtime_state", AsyncMock(return_value=state)):
            assert await msa._rehydrate_agent("sess-1") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_legacy_state_lacks_tunnel(self) -> None:
        # Old exec-mode rows have no tunnel_url / opencode_session_id —
        # force fresh spawn so we get a tunneled sandbox.
        state = _live_state(tunnel_url=None, opencode_session_id=None)
        with patch.object(msa, "_load_runtime_state", AsyncMock(return_value=state)):
            assert await msa._rehydrate_agent("sess-1") is None

    @pytest.mark.asyncio
    async def test_returns_none_on_register_failure(self) -> None:
        spawner = MagicMock()
        spawner.register_foreign_sandbox = AsyncMock(return_value=False)
        with (
            patch.object(
                msa, "_load_runtime_state", AsyncMock(return_value=_live_state())
            ),
            patch.object(msa, "_persist_runtime_state", AsyncMock()),
            patch(
                "omoi_os.services.modal_spawner.get_modal_spawner",
                return_value=spawner,
            ),
        ):
            assert await msa._rehydrate_agent("sess-1") is None

    @pytest.mark.asyncio
    async def test_returns_none_on_unhealthy_tunnel(self) -> None:
        spawner = MagicMock()
        spawner.register_foreign_sandbox = AsyncMock(return_value=True)
        with (
            patch.object(
                msa, "_load_runtime_state", AsyncMock(return_value=_live_state())
            ),
            patch.object(msa, "_persist_runtime_state", AsyncMock()),
            patch.object(msa, "_probe_tunnel_alive", AsyncMock(return_value=False)),
            patch(
                "omoi_os.services.modal_spawner.get_modal_spawner",
                return_value=spawner,
            ),
        ):
            assert await msa._rehydrate_agent("sess-1") is None

    @pytest.mark.asyncio
    async def test_recreates_session_when_opencode_lost_it(self) -> None:
        spawner = MagicMock()
        spawner.register_foreign_sandbox = AsyncMock(return_value=True)
        with (
            patch.object(
                msa, "_load_runtime_state", AsyncMock(return_value=_live_state())
            ),
            patch.object(msa, "_persist_runtime_state", AsyncMock()),
            patch.object(msa, "_probe_tunnel_alive", AsyncMock(return_value=True)),
            patch.object(
                msa, "_opencode_session_exists", AsyncMock(return_value=False)
            ),
            patch.object(
                msa, "_create_opencode_session", AsyncMock(return_value="ses_new")
            ),
            patch(
                "omoi_os.services.modal_spawner.get_modal_spawner",
                return_value=spawner,
            ),
        ):
            agent = await msa._rehydrate_agent("sess-1")
        assert agent is not None
        assert agent.opencode_session_id == "ses_new"

    @pytest.mark.asyncio
    async def test_returns_agent_on_full_success(self) -> None:
        spawner = MagicMock()
        spawner.register_foreign_sandbox = AsyncMock(return_value=True)
        with (
            patch.object(
                msa, "_load_runtime_state", AsyncMock(return_value=_live_state())
            ),
            patch.object(msa, "_probe_tunnel_alive", AsyncMock(return_value=True)),
            patch.object(msa, "_opencode_session_exists", AsyncMock(return_value=True)),
            patch(
                "omoi_os.services.modal_spawner.get_modal_spawner",
                return_value=spawner,
            ),
        ):
            agent = await msa._rehydrate_agent("sess-1")
        assert agent is not None
        assert agent.sandbox_id == "sb-1"
        assert agent.modal_object_id == "modal-abc"
        assert agent.tunnel_url == "https://t.modal.host"
        assert agent.opencode_session_id == "ses_persisted"
        assert agent.provider == "fireworks-ai"
        spawner.register_foreign_sandbox.assert_awaited_once_with(
            "sb-1", "modal-abc", task_id="sess-1"
        )
