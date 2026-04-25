"""Unit tests for the per-session Redis channel path.

Verifies:
  - `EventBusService.publish_to_session` publishes to `ch.{session_id}`
  - It's a no-op when Redis is unavailable (same graceful-degradation
    pattern as the legacy `publish`)
  - `SessionChannelManager` tracks per-session subscriptions and releases
    them when the last local participant leaves
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from omoi_os.api.routes.session_channel import SessionChannelManager
from omoi_os.services.event_bus import EventBusService


def _make_bus_with_fake_redis() -> tuple[EventBusService, MagicMock]:
    """Construct an EventBusService with a fake redis client attached.

    We bypass `__init__` to avoid the real `redis.from_url` + ping.
    """
    bus = EventBusService.__new__(EventBusService)
    fake_redis = MagicMock()
    bus.redis_client = fake_redis
    bus.pubsub = fake_redis.pubsub.return_value
    bus._available = True
    return bus, fake_redis


def test_publish_to_session_writes_to_ch_channel():
    bus, fake_redis = _make_bus_with_fake_redis()
    bus.publish_to_session(
        "sid-123",
        {"type": "cursor.moved", "data": {"x": 1}},
    )
    fake_redis.publish.assert_called_once()
    channel, payload = fake_redis.publish.call_args.args
    assert channel == "ch.sid-123"
    assert '"cursor.moved"' in payload
    assert '"x": 1' in payload


def test_publish_to_session_noop_when_redis_unavailable():
    bus = EventBusService.__new__(EventBusService)
    bus.redis_client = None
    bus.pubsub = None
    bus._available = False
    # Must not raise
    bus.publish_to_session("sid-x", {"type": "t"})


def test_publish_to_session_swallows_connection_errors():
    import redis

    bus, fake_redis = _make_bus_with_fake_redis()
    fake_redis.publish.side_effect = redis.exceptions.ConnectionError("down")
    # Must not raise
    bus.publish_to_session("sid", {"type": "t"})


@pytest.mark.asyncio
async def test_channel_manager_subscribes_on_first_join_unsubscribes_on_last_leave(
    monkeypatch,
):
    m = SessionChannelManager()
    # Set up a fake pubsub on the manager so `_subscribe_session` can exercise it.
    fake_pubsub = MagicMock()
    m._bus_pubsub = fake_pubsub

    sid = "sid-abc"

    # First join → subscribe should be called once.
    await m._subscribe_session(sid)
    fake_pubsub.subscribe.assert_called_once_with(f"ch.{sid}")
    assert sid in m._subscribed_sessions

    # Second call (duplicate) is idempotent — no new subscribe.
    fake_pubsub.subscribe.reset_mock()
    await m._subscribe_session(sid)
    fake_pubsub.subscribe.assert_not_called()

    # Unsubscribe → channel released.
    await m._unsubscribe_session(sid)
    fake_pubsub.unsubscribe.assert_called_once_with(f"ch.{sid}")
    assert sid not in m._subscribed_sessions

    # Second unsubscribe is idempotent.
    fake_pubsub.unsubscribe.reset_mock()
    await m._unsubscribe_session(sid)
    fake_pubsub.unsubscribe.assert_not_called()


@pytest.mark.asyncio
async def test_channel_manager_handles_subscribe_without_pubsub():
    """If ensure_bus_bridge wasn't called, subscribe/unsubscribe should no-op."""
    m = SessionChannelManager()
    # `_bus_pubsub` is None by default
    await m._subscribe_session("sid")  # must not raise
    await m._unsubscribe_session("sid")
    assert "sid" not in m._subscribed_sessions
