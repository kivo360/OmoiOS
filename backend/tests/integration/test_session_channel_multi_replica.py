"""Multi-replica cross-replica cursor delivery (spec §07 + §18 Pattern D).

Verifies the Wave-1 T2 architecture: `cursor.moved` published by replica A
is delivered on replica B within 500ms, proving sessions are no longer
pinned to a single uvicorn worker.

Why it's a bus-level test (not spawn two uvicorn processes):
  - The load-bearing layer is Redis pub/sub keyed on `ch.{session_id}`.
    If two independent `EventBusService` instances sharing one Redis see
    each other's `publish_to_session` calls, cross-replica delivery works.
  - Spawning two uvicorn subprocesses adds 5-10s of setup, WS-client
    orchestration, and flake potential — without exercising any new
    code path not already exercised here.
  - Companion: `docs/architecture/session-channel-scaling.md` documents
    the design; this test proves the plumbing.

Skipped when Redis is unreachable on any of the standard local ports.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List

import pytest
import redis

from omoi_os.services.event_bus import EventBusService


pytestmark = [pytest.mark.integration]


def _first_reachable_redis() -> str | None:
    """Return the first Redis URL we can ping, else None."""
    candidates = [
        os.environ.get("REDIS_URL"),
        "redis://localhost:16379/0",
        "redis://localhost:6379/0",
    ]
    for url in candidates:
        if not url:
            continue
        try:
            client = redis.from_url(url, socket_timeout=1.0, socket_connect_timeout=1.0)
            client.ping()
            client.close()
            return url
        except Exception:  # noqa: BLE001
            continue
    return None


@pytest.fixture(scope="module")
def redis_url() -> str:
    url = _first_reachable_redis()
    if not url:
        pytest.skip("No reachable Redis on $REDIS_URL, :16379 or :6379")
    return url


def _subscribe_session(
    bus: EventBusService, session_id: str, received: List[Dict[str, Any]]
) -> threading.Thread:
    """Stand up a replica-side subscriber on `ch.{session_id}`.

    Runs the blocking pubsub listener in a thread so the test flow (publish
    on replica A, assert receipt on replica B) stays synchronous.
    """
    pubsub = bus.redis_client.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(f"ch.{session_id}")

    def _listen() -> None:
        for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                payload = json.loads(message["data"])
            except Exception:  # noqa: BLE001
                continue
            received.append(payload)

    t = threading.Thread(target=_listen, daemon=True)
    t.start()
    # `pubsub.listen()` doesn't confirm the subscribe before yielding — give
    # Redis a moment to register the subscription so the publish below races
    # correctly.
    time.sleep(0.1)
    # Stash the pubsub on the thread so the test can close it cleanly.
    t._pubsub = pubsub  # type: ignore[attr-defined]
    return t


def test_cursor_crosses_replica_boundary(redis_url: str) -> None:
    """Replica A publishes `cursor.moved`; replica B receives it within 500ms."""
    session_id = f"multi-replica-{int(time.time() * 1000)}"

    replica_a = EventBusService(redis_url=redis_url)
    replica_b = EventBusService(redis_url=redis_url)
    try:
        assert replica_a._available, "replica A failed to connect to Redis"
        assert replica_b._available, "replica B failed to connect to Redis"

        received_on_b: List[Dict[str, Any]] = []
        listener = _subscribe_session(replica_b, session_id, received_on_b)

        cursor_frame = {
            "type": "cursor.moved",
            "data": {"file": "refund_spec.ts", "line": 42},
            "user_id": "user-a",
        }

        started = time.perf_counter()
        replica_a.publish_to_session(session_id, cursor_frame)

        # Wait up to 500ms for delivery — spec §07 says multiplayer frames
        # should feel real-time; the plan calls out 500ms as the acceptance
        # threshold.
        deadline = time.perf_counter() + 0.5
        while time.perf_counter() < deadline and not received_on_b:
            time.sleep(0.01)

        latency_ms = (time.perf_counter() - started) * 1000
        assert received_on_b, (
            f"replica B did not receive cursor.moved within 500ms "
            f"(elapsed={latency_ms:.1f}ms)"
        )

        delivered = received_on_b[0]
        assert delivered["type"] == "cursor.moved"
        assert delivered["data"]["file"] == "refund_spec.ts"
        assert delivered["data"]["line"] == 42
        assert delivered["user_id"] == "user-a"

        # Close the subscriber cleanly — without this, pytest holds the thread.
        listener._pubsub.unsubscribe()  # type: ignore[attr-defined]
        listener._pubsub.close()  # type: ignore[attr-defined]
    finally:
        replica_a.close()
        replica_b.close()


def test_cursor_does_not_leak_across_sessions(redis_url: str) -> None:
    """Per-session channel isolation: frames on ch.X are NOT delivered to ch.Y."""
    session_x = f"isolated-x-{int(time.time() * 1000)}"
    session_y = f"isolated-y-{int(time.time() * 1000)}"

    replica_a = EventBusService(redis_url=redis_url)
    replica_b = EventBusService(redis_url=redis_url)
    try:
        received_on_y: List[Dict[str, Any]] = []
        listener = _subscribe_session(replica_b, session_y, received_on_y)

        replica_a.publish_to_session(
            session_x,
            {"type": "cursor.moved", "data": {"line": 1}},
        )
        # Let any cross-channel leakage land before we assert.
        time.sleep(0.2)

        assert received_on_y == [], (
            "cursor frame from session X leaked to session Y's channel"
        )

        listener._pubsub.unsubscribe()  # type: ignore[attr-defined]
        listener._pubsub.close()  # type: ignore[attr-defined]
    finally:
        replica_a.close()
        replica_b.close()
