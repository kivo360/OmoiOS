"""Integration tests for the spec §03 session surface endpoints.

Covers the six new routes added by the sessions-surface-spec-alignment plan:
events SSE (replay only — live branch is asserted in the smoke test),
messages (reply), fork, share, artifacts.

Each test drives the FastAPI app with an authenticated test user whose org
matches the task's ticket's project's org, so `verify_task_access` passes.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from omoi_os.models.event import Event
from omoi_os.models.session_acl import SessionACL, SessionFork
from omoi_os.models.task import Task


pytestmark = [pytest.mark.integration]


# ── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def session_feature_flags(monkeypatch):
    """Flip sessions_api_v1 on and force the event bus into
    Redis-unavailable mode so the SSE handler exits after replay (tests
    assert replay behavior only; live branch is covered by the smoke test).
    """

    def _enabled(flag_name: str) -> bool:
        return flag_name in {"sessions_api_v1", "artifacts_unified_v1"}

    monkeypatch.setattr("omoi_os.api.routes.sessions.is_feature_enabled", _enabled)

    # Force bus into "Redis unavailable" mode so the live-subscribe branch of
    # the SSE generator exits cleanly after replay. Otherwise TestClient's
    # synchronous iter_lines + break doesn't interrupt the blocking pubsub
    # read fast enough to finish the test run.
    class _UnavailableBus:
        _available = False
        redis_client = None

        def publish(self, *a, **k):
            pass

    def _fake_bus():
        return _UnavailableBus()

    monkeypatch.setattr("omoi_os.api.dependencies.get_event_bus_service", _fake_bus)
    yield


@pytest.fixture
def auth_override(app, test_user, monkeypatch):
    """Bypass the Bearer auth + ticket-RBAC layers for isolated session tests.

    The new session endpoints call `verify_task_access` directly (not via
    `Depends`), so `dependency_overrides` doesn't catch them — we monkeypatch
    the module-level reference instead. ACL logic we DO want to test lives in
    `session_acls`, which these tests exercise directly.
    """
    from omoi_os.api.dependencies import get_current_user

    async def _user_override():
        return test_user

    async def _access_passthrough(task_id: str, *args, **kwargs):
        return task_id

    app.dependency_overrides[get_current_user] = _user_override
    monkeypatch.setattr(
        "omoi_os.api.routes.sessions.verify_task_access",
        _access_passthrough,
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def app():
    """Build an isolated FastAPI app mounting just the sessions router."""
    from fastapi import FastAPI

    from omoi_os.api.routes import sessions as sessions_module

    app = FastAPI()
    app.include_router(sessions_module.router, prefix="/api/v1/sessions")
    return app


@pytest.fixture
def client(app, session_feature_flags, auth_override):
    return TestClient(app)


@pytest.fixture
def session_task(db_service, sample_ticket):
    """Persist a Task and return its id — this is the 'session'."""
    from omoi_os.services.database import DatabaseService

    db: DatabaseService = db_service
    with db.get_session() as session:
        t = Task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implementation",
            title="integration-session",
            description="session surface test",
            priority="MEDIUM",
            status="pending",
        )
        session.add(t)
        session.flush()
        tid = t.id
        session.commit()
    yield tid


# ── envelope helper ─────────────────────────────────────────────────────────


def _seed_events(db_service, session_id: str, count: int) -> list[int]:
    """Insert `count` envelope-shaped events with monotonic seq 1..count."""
    from omoi_os.services.event_bus import EventBusService
    from omoi_os.services.session_event_envelope import (
        ACTOR_AGENT,
        SessionEventEnvelope,
    )

    class _Bus(EventBusService):
        def __init__(self):
            self._available = False

        def publish(self, event):
            pass

    seqs = []
    with db_service.get_session() as session:
        envelope = SessionEventEnvelope(session, _Bus())
        for i in range(count):
            env = envelope.emit(
                session_id=session_id,
                event_type="tool_call",
                actor=ACTOR_AGENT,
                data={"i": i},
            )
            seqs.append(env["seq"])
        session.commit()
    return seqs


# ── tests ───────────────────────────────────────────────────────────────────


class TestSessionEvents:
    """GET /api/v1/sessions/{id}/events — SSE replay branch."""

    def test_replays_events_in_seq_order(self, client, db_service, session_task):
        _seed_events(db_service, session_task, 3)

        # TestClient supports iter_lines; stream mode prevents auto-decoding.
        with client.stream(
            "GET",
            f"/api/v1/sessions/{session_task}/events",
            headers={"Accept": "text/event-stream"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

            # Drain the replay frames (we close the stream before live mode
            # would produce anything, which is fine for a replay-only assertion).
            seen = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    seen.append(json.loads(line[6:]))
                if len(seen) >= 3:
                    break

        assert len(seen) == 3
        assert [e["seq"] for e in seen] == [1, 2, 3]
        assert all(e["session_id"] == session_task for e in seen)
        assert all(e["type"] == "tool_call" for e in seen)

    def test_last_event_id_resume(self, client, db_service, session_task):
        _seed_events(db_service, session_task, 5)

        with client.stream(
            "GET",
            f"/api/v1/sessions/{session_task}/events",
            headers={"Accept": "text/event-stream", "Last-Event-ID": "2"},
        ) as response:
            assert response.status_code == 200
            seen = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    seen.append(json.loads(line[6:]))
                if len(seen) >= 3:
                    break

        assert [e["seq"] for e in seen] == [3, 4, 5]


class TestSessionReply:
    """POST /api/v1/sessions/{id}/messages."""

    def test_reply_emits_envelope(self, client, db_service, session_task, test_user):
        response = client.post(
            f"/api/v1/sessions/{session_task}/messages",
            json={"text": "add a regression test"},
        )
        assert response.status_code == 204

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
            assert evt.seq == 1

    def test_reply_rejects_empty_text(self, client, session_task):
        response = client.post(
            f"/api/v1/sessions/{session_task}/messages",
            json={"text": ""},
        )
        assert response.status_code == 422


class TestSessionShare:
    """POST /api/v1/sessions/{id}/share — ACL upsert."""

    def test_grants_viewer_role(self, client, db_service, session_task, test_user):
        peer_id = uuid4()
        # Put the peer in the DB so FK resolves.
        from omoi_os.models.user import User

        with db_service.get_session() as session:
            session.add(
                User(
                    id=peer_id,
                    email=f"peer-{peer_id}@test",
                    hashed_password="x",
                    full_name="Peer Tester",
                    is_active=True,
                    is_verified=True,
                )
            )
            session.commit()

        response = client.post(
            f"/api/v1/sessions/{session_task}/share",
            json={"grants": [{"user_id": str(peer_id), "role": "viewer"}]},
        )
        assert response.status_code == 200
        assert response.json()["granted"] == 1

        with db_service.get_session() as session:
            acl = (
                session.query(SessionACL)
                .filter(
                    SessionACL.task_id == session_task,
                    SessionACL.user_id == peer_id,
                )
                .one()
            )
            assert acl.role == "viewer"

    def test_rejects_invalid_role(self, client, session_task):
        response = client.post(
            f"/api/v1/sessions/{session_task}/share",
            json={"grants": [{"user_id": str(uuid4()), "role": "admin"}]},
        )
        assert response.status_code == 422


class TestSessionFork:
    """POST /api/v1/sessions/{id}/fork."""

    def test_fork_copies_events_up_to_seq(
        self, client, db_service, session_task, test_user
    ):
        _seed_events(db_service, session_task, 5)

        response = client.post(
            f"/api/v1/sessions/{session_task}/fork",
            json={"from_seq": 3, "prompt": "try a different approach"},
        )
        assert response.status_code == 201
        body = response.json()
        child_id = body["id"]
        assert body["parent_session_id"] == session_task
        assert body["from_seq"] == 3

        with db_service.get_session() as session:
            child_events = (
                session.query(Event)
                .filter(Event.entity_id == child_id)
                .order_by(Event.seq.asc())
                .all()
            )
            assert [e.seq for e in child_events] == [1, 2, 3]

            parent_events = (
                session.query(Event)
                .filter(Event.entity_id == session_task)
                .order_by(Event.seq.asc())
                .all()
            )
            assert [e.seq for e in parent_events] == [1, 2, 3, 4, 5]

            fork = (
                session.query(SessionFork)
                .filter(SessionFork.child_task_id == child_id)
                .one()
            )
            assert fork.parent_task_id == session_task
            assert fork.from_seq == 3

            owner_acl = (
                session.query(SessionACL)
                .filter(
                    SessionACL.task_id == child_id,
                    SessionACL.user_id == test_user.id,
                )
                .one()
            )
            assert owner_acl.role == "owner"


class TestSessionArtifacts:
    """GET /api/v1/sessions/{id}/artifacts."""

    def test_filters_by_task_id_metadata(
        self, client, db_service, session_task, test_user
    ):
        from omoi_os.models.artifact import Artifact
        from omoi_os.models.workspace import Workspace
        from omoi_os.models.organization import Organization

        with db_service.get_session() as session:
            org = Organization(
                name="art-test-org",
                slug=f"org-{uuid4().hex[:8]}",
                owner_id=test_user.id,
            )
            session.add(org)
            session.flush()

            ws = Workspace(
                organization_id=org.id, name="art-test-ws", slug=f"ws-{uuid4().hex[:8]}"
            )
            session.add(ws)
            session.flush()

            a = Artifact(
                workspace_id=ws.id,
                name="output.txt",
                storage_backend="local",
                storage_path=f"/tmp/art-{uuid4().hex[:8]}.txt",
                checksum="sha256:abc",
                size_bytes=100,
                content_type="text/plain",
                artifact_metadata={"task_id": session_task},
            )
            b = Artifact(
                workspace_id=ws.id,
                name="unrelated.txt",
                storage_backend="local",
                storage_path=f"/tmp/art-{uuid4().hex[:8]}.txt",
                checksum="sha256:def",
                size_bytes=200,
                content_type="text/plain",
                artifact_metadata={"task_id": "some-other-task"},
            )
            session.add(a)
            session.add(b)
            session.commit()

        response = client.get(f"/api/v1/sessions/{session_task}/artifacts")
        assert response.status_code == 200
        names = {item["name"] for item in response.json()}
        assert names == {"output.txt"}
