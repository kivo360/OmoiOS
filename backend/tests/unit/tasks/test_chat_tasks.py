"""Unit tests for the chat-responder Taskiq task wrapper.

The actual response logic lives in `chat_responder.respond_to_session`
and is exercised by other tests; this module covers the Taskiq adapter
+ schedule_response's broker-or-fallback wiring.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_enqueue_response_returns_handle_on_success() -> None:
    from omoi_os.tasks import chat_tasks

    fake_handle = MagicMock(name="taskiq_handle")
    with patch.object(
        chat_tasks.respond_to_session_task,
        "kiq",
        AsyncMock(return_value=fake_handle),
    ):
        result = await chat_tasks.enqueue_response("sess-1")
    assert result is fake_handle


@pytest.mark.asyncio
async def test_enqueue_response_returns_none_when_broker_down() -> None:
    """Broker enqueue raising must surface as None so the caller can fall back."""
    from omoi_os.tasks import chat_tasks

    with patch.object(
        chat_tasks.respond_to_session_task,
        "kiq",
        AsyncMock(side_effect=ConnectionError("redis down")),
    ):
        result = await chat_tasks.enqueue_response("sess-1")
    assert result is None


@pytest.mark.asyncio
async def test_schedule_response_uses_broker_when_available() -> None:
    """Successful enqueue → no in-process respond_to_session call."""
    from omoi_os.services import chat_responder

    fake_handle = MagicMock()
    fake_db = MagicMock()
    with (
        patch(
            "omoi_os.tasks.chat_tasks.enqueue_response",
            AsyncMock(return_value=fake_handle),
        ),
        patch.object(chat_responder, "respond_to_session", AsyncMock()) as in_process,
    ):
        task = chat_responder.schedule_response("sess-broker", fake_db)
        await task

    in_process.assert_not_awaited()


@pytest.mark.asyncio
async def test_schedule_response_falls_back_when_broker_returns_none() -> None:
    """Enqueue returning None → in-process respond_to_session runs."""
    from omoi_os.services import chat_responder

    fake_db = MagicMock()
    with (
        patch(
            "omoi_os.tasks.chat_tasks.enqueue_response",
            AsyncMock(return_value=None),
        ),
        patch.object(chat_responder, "respond_to_session", AsyncMock()) as in_process,
    ):
        task = chat_responder.schedule_response("sess-fallback", fake_db)
        await task

    in_process.assert_awaited_once_with("sess-fallback", db=fake_db)


@pytest.mark.asyncio
async def test_schedule_response_falls_back_when_enqueue_raises() -> None:
    """Enqueue raising → caught + in-process respond_to_session runs."""
    from omoi_os.services import chat_responder

    fake_db = MagicMock()
    with (
        patch(
            "omoi_os.tasks.chat_tasks.enqueue_response",
            AsyncMock(side_effect=RuntimeError("import-time boom")),
        ),
        patch.object(chat_responder, "respond_to_session", AsyncMock()) as in_process,
    ):
        task = chat_responder.schedule_response("sess-raise", fake_db)
        await task

    in_process.assert_awaited_once_with("sess-raise", db=fake_db)
