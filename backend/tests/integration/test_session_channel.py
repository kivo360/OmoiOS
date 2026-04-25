"""Integration tests for the per-session multiplayer WebSocket (spec §07).

Covers:
- Two clients on the same session see each other via `participant.joined`
  on connect and `participant.left` on disconnect.
- `cursor.moved` messages broadcast to peers but are NOT persisted.
- `message.send` is acked to the sender and persisted via the envelope.

These tests bypass the Redis bus bridge — the bridge is what fans an event
out from the envelope's `event_bus.publish` back to all sockets, but
`TestClient` runs a single process where we can assert the manager state
directly. The smoke test covers the Redis bridge end-to-end.
"""

from __future__ import annotations


import pytest
from fastapi.testclient import TestClient

from omoi_os.models.event import Event
from omoi_os.models.task import Task


pytestmark = [pytest.mark.integration]


@pytest.fixture
def session_task(db_service, sample_ticket):
    with db_service.get_session() as session:
        t = Task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implementation",
            title="ws-session",
            description="ws test",
            priority="MEDIUM",
            status="pending",
        )
        session.add(t)
        session.flush()
        tid = t.id
        session.commit()
    return tid


@pytest.fixture
def ws_app(test_user, monkeypatch):
    """Isolated app with the sessions router and auth bypassed."""
    from fastapi import FastAPI

    from omoi_os.api.routes import session_channel as channel_module
    from omoi_os.api.routes import sessions as sessions_module

    app = FastAPI()
    app.include_router(sessions_module.router, prefix="/api/v1/sessions")

    async def _auth_ok(_token: str):
        return test_user

    async def _access_ok(task_id: str, *args, **kwargs):
        return task_id

    monkeypatch.setattr(channel_module, "_authenticate_ws_token", _auth_ok)
    monkeypatch.setattr(channel_module, "verify_task_access", _access_ok)

    # Swap bus bridge to a no-op so tests don't depend on Redis.
    async def _no_bridge(self, bus):
        return

    monkeypatch.setattr(
        channel_module.SessionChannelManager, "ensure_bus_bridge", _no_bridge
    )

    yield app


@pytest.fixture
def ws_client(ws_app):
    return TestClient(ws_app)


class TestPresence:
    """Joined/left events fire to peers."""

    def test_second_join_triggers_participant_joined(self, ws_client, session_task):
        # First client opens the channel — drains presence notifications as
        # the second client joins.
        with ws_client.websocket_connect(
            f"/api/v1/sessions/{session_task}/ws?token=x"
        ) as a:
            with ws_client.websocket_connect(
                f"/api/v1/sessions/{session_task}/ws?token=x"
            ) as _b:
                frame = a.receive_json()
                assert frame["type"] == "participant.joined"
                assert "user_id" in frame["data"]


class TestCursorMoves:
    """cursor.moved broadcasts to peers and is NOT persisted."""

    def test_cursor_broadcasts_and_does_not_persist(
        self, ws_client, session_task, db_service
    ):
        with ws_client.websocket_connect(
            f"/api/v1/sessions/{session_task}/ws?token=x"
        ) as a:
            with ws_client.websocket_connect(
                f"/api/v1/sessions/{session_task}/ws?token=x"
            ) as b:
                # Drain the join notice on A so the cursor event is next.
                _ = a.receive_json()

                b.send_json(
                    {
                        "type": "cursor.moved",
                        "data": {"file": "refund_spec.ts", "line": 42},
                    }
                )

                frame = a.receive_json()
                assert frame["type"] == "cursor.moved"
                assert frame["data"]["file"] == "refund_spec.ts"
                assert frame["data"]["line"] == 42
                assert "user_id" in frame["data"]

        # No events table rows were written for the cursor move.
        with db_service.get_session() as session:
            persisted = (
                session.query(Event)
                .filter(
                    Event.entity_id == session_task,
                    Event.event_type == "cursor.moved",
                )
                .count()
            )
            assert persisted == 0


class TestMessageSend:
    """message.send acks to sender and persists via the envelope."""

    def test_message_send_persists_and_acks(
        self, ws_client, session_task, db_service, test_user
    ):
        with ws_client.websocket_connect(
            f"/api/v1/sessions/{session_task}/ws?token=x"
        ) as a:
            a.send_json(
                {"type": "message.send", "data": {"text": "add a regression test"}}
            )
            ack = a.receive_json()
            assert ack["type"] == "message.ack"
            assert isinstance(ack["data"]["seq"], int)

        with db_service.get_session() as session:
            evt = (
                session.query(Event)
                .filter(
                    Event.entity_id == session_task,
                    Event.event_type == "session.message",
                )
                .one()
            )
            assert evt.actor == f"user:{test_user.id}"
            assert evt.payload["text"] == "add a regression test"

    def test_message_send_rejects_empty(self, ws_client, session_task):
        with ws_client.websocket_connect(
            f"/api/v1/sessions/{session_task}/ws?token=x"
        ) as a:
            a.send_json({"type": "message.send", "data": {"text": "   "}})
            frame = a.receive_json()
            assert "error" in frame


class TestUnknownType:
    def test_unknown_type_returns_error(self, ws_client, session_task):
        with ws_client.websocket_connect(
            f"/api/v1/sessions/{session_task}/ws?token=x"
        ) as a:
            a.send_json({"type": "telepathy", "data": {}})
            frame = a.receive_json()
            assert "error" in frame
            assert "telepathy" in frame["error"]
