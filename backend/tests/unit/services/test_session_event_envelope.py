"""Unit tests for SessionEventEnvelope."""

from __future__ import annotations

import pytest

from omoi_os.models.event import Event
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.session_event_envelope import (
    ACTOR_AGENT,
    SessionEventEnvelope,
    actor_user,
)


pytestmark = pytest.mark.unit


class _RecordingBus(EventBusService):
    """Bus stub that records publishes without needing a live Redis."""

    def __init__(self) -> None:  # noqa: D401 — keep super() init out; we don't want a real client
        self.published: list = []
        self._available = False  # EventBusService.publish no-ops when False

    def publish(self, event):  # type: ignore[override]
        self.published.append(event)


def _new_task(db_service: DatabaseService, sample_ticket) -> str:
    """Insert a minimal task row so envelope FK resolves; return task.id."""
    from omoi_os.models.task import Task

    with db_service.get_session() as session:
        task = Task(
            ticket_id=sample_ticket.id,
            description="envelope test task",
            status="pending",
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implementation",
            title="envelope test",
            priority="MEDIUM",
        )
        session.add(task)
        session.flush()
        tid = task.id
        session.commit()
        return tid


def test_emit_assigns_monotonic_seq(db_service: DatabaseService, sample_ticket):
    """Three emits for one session produce seq = 1, 2, 3 in order."""
    task_id = _new_task(db_service, sample_ticket)
    bus = _RecordingBus()

    with db_service.get_session() as session:
        envelope = SessionEventEnvelope(session, bus)
        first = envelope.emit(
            session_id=task_id,
            event_type="session.started",
            actor=ACTOR_AGENT,
            data={"note": "first"},
        )
        second = envelope.emit(
            session_id=task_id,
            event_type="tool_call",
            actor=ACTOR_AGENT,
            data={"tool": "bash"},
        )
        third = envelope.emit(
            session_id=task_id,
            event_type="tool_result",
            actor=ACTOR_AGENT,
            data={"rc": 0},
        )
        session.commit()

    assert first["seq"] == 1
    assert second["seq"] == 2
    assert third["seq"] == 3

    # All three persisted and queryable in order.
    with db_service.get_session() as session:
        rows = (
            session.query(Event)
            .filter(Event.entity_id == task_id)
            .order_by(Event.seq.asc())
            .all()
        )
        assert [r.seq for r in rows] == [1, 2, 3]
        assert [r.event_type for r in rows] == [
            "session.started",
            "tool_call",
            "tool_result",
        ]
        assert all(r.actor == ACTOR_AGENT for r in rows)

    # Bus got one publish per emit with the envelope nested under payload.
    assert len(bus.published) == 3
    assert bus.published[0].payload["envelope"]["seq"] == 1
    assert bus.published[0].entity_id == task_id


def test_emit_isolates_seq_between_sessions(db_service: DatabaseService, sample_ticket):
    """Two separate sessions keep independent seq sequences."""
    task_a = _new_task(db_service, sample_ticket)
    task_b = _new_task(db_service, sample_ticket)
    bus = _RecordingBus()

    with db_service.get_session() as session:
        envelope = SessionEventEnvelope(session, bus)
        envelope.emit(session_id=task_a, event_type="x", actor=ACTOR_AGENT)
        envelope.emit(session_id=task_b, event_type="x", actor=ACTOR_AGENT)
        envelope.emit(session_id=task_a, event_type="x", actor=ACTOR_AGENT)
        envelope.emit(session_id=task_b, event_type="x", actor=ACTOR_AGENT)
        session.commit()

    with db_service.get_session() as session:
        a = (
            session.query(Event.seq)
            .filter(Event.entity_id == task_a)
            .order_by(Event.seq)
            .all()
        )
        b = (
            session.query(Event.seq)
            .filter(Event.entity_id == task_b)
            .order_by(Event.seq)
            .all()
        )
        assert [r.seq for r in a] == [1, 2]
        assert [r.seq for r in b] == [1, 2]


def test_emit_records_user_actor(db_service: DatabaseService, sample_ticket, test_user):
    """actor_user(uuid) serializes as 'user:<uuid>' on persisted row."""
    task_id = _new_task(db_service, sample_ticket)
    bus = _RecordingBus()

    with db_service.get_session() as session:
        SessionEventEnvelope(session, bus).emit(
            session_id=task_id,
            event_type="session.message",
            actor=actor_user(test_user.id),
            data={"text": "hi"},
        )
        session.commit()

    with db_service.get_session() as session:
        row = session.query(Event).filter(Event.entity_id == task_id).one()
        assert row.actor == f"user:{test_user.id}"
        assert row.seq == 1


def test_emit_requires_session_id(db_service: DatabaseService):
    """Empty session_id raises before any DB work happens."""
    bus = _RecordingBus()
    with db_service.get_session() as session:
        envelope = SessionEventEnvelope(session, bus)
        with pytest.raises(ValueError, match="session_id"):
            envelope.emit(session_id="", event_type="x", actor=ACTOR_AGENT)
        with pytest.raises(ValueError, match="event_type"):
            envelope.emit(session_id="some-id", event_type="", actor=ACTOR_AGENT)
