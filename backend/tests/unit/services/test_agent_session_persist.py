"""Unit tests for OmoiOsSessionPersistDriver helper functions.

Covers cursor parsing, datetime/unix conversions, sender translation, and
the row<->record converters. Full DB-backed integration tests for the 5 async
methods land in tests/integration/services/test_agent_session_persist.py
(Task #8 — smoke probe + integration).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from sandboxagent import SessionPersistDriver

from omoi_os.services.agent_session_persist import (
    OmoiOsSessionPersistDriver,
    _AGENT_SESSION_KEY,
    _DEFAULT_EVENT_TYPE,
    _event_row_to_session_event,
    _from_unix_dt,
    _from_unix_iso,
    _parse_cursor,
    _parse_iso_to_unix,
    _task_to_session_record,
    _to_unix_int,
    _translate_sender,
    _untranslate_sender,
)


pytestmark = pytest.mark.unit


class TestParseCursor:
    def test_none_returns_zero(self) -> None:
        assert _parse_cursor(None) == 0

    def test_empty_string_returns_zero(self) -> None:
        assert _parse_cursor("") == 0

    def test_valid_int_string(self) -> None:
        assert _parse_cursor("42") == 42

    def test_negative_returns_zero(self) -> None:
        assert _parse_cursor("-5") == 0

    def test_invalid_returns_zero(self) -> None:
        assert _parse_cursor("not-a-number") == 0


class TestUnixConversions:
    def test_to_unix_int_from_datetime(self) -> None:
        dt = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
        assert _to_unix_int(dt) == int(dt.timestamp())

    def test_to_unix_int_from_int(self) -> None:
        assert _to_unix_int(1745678400) == 1745678400

    def test_to_unix_int_from_none(self) -> None:
        assert _to_unix_int(None) == 0

    def test_from_unix_dt_returns_utc(self) -> None:
        dt = _from_unix_dt(1745678400)
        assert dt.tzinfo is timezone.utc

    def test_from_unix_iso_returns_iso_string(self) -> None:
        iso = _from_unix_iso(1745678400)
        assert iso is not None
        # Round-trip back: parse our ISO output, compare to the original int
        parsed_back = _parse_iso_to_unix(iso)
        assert parsed_back == 1745678400

    def test_from_unix_iso_none_passthrough(self) -> None:
        assert _from_unix_iso(None) is None

    def test_parse_iso_to_unix_none_passthrough(self) -> None:
        assert _parse_iso_to_unix(None) is None

    def test_parse_iso_to_unix_invalid_returns_none(self) -> None:
        assert _parse_iso_to_unix("not-an-iso") is None


class TestSenderTranslation:
    def test_agent_passes_through(self) -> None:
        assert (
            _translate_sender("agent", created_by=None, connection_id="c1") == "agent"
        )

    def test_client_with_created_by(self) -> None:
        uid = UUID("11111111-2222-3333-4444-555555555555")
        assert (
            _translate_sender("client", created_by=uid, connection_id="c1")
            == f"user:{uid}"
        )

    def test_client_without_created_by_uses_connection(self) -> None:
        assert (
            _translate_sender("client", created_by=None, connection_id="conn-7")
            == "user:conn-7"
        )

    def test_client_no_created_by_no_connection_uses_anon(self) -> None:
        assert (
            _translate_sender("client", created_by=None, connection_id="")
            == "user:anon"
        )

    def test_unknown_sender_passes_through(self) -> None:
        assert (
            _translate_sender("system", created_by=None, connection_id="c1") == "system"
        )

    def test_untranslate_agent(self) -> None:
        assert _untranslate_sender("agent") == "agent"

    def test_untranslate_user_prefix(self) -> None:
        assert _untranslate_sender("user:abc-123") == "client"

    def test_untranslate_passes_through(self) -> None:
        assert _untranslate_sender("system") == "system"

    def test_untranslate_empty(self) -> None:
        assert _untranslate_sender("") == ""


class TestTaskToSessionRecord:
    def _make_task(self, *, result: dict | None) -> MagicMock:
        task = MagicMock()
        task.id = "task-1"
        task.created_at = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
        task.sandbox_id = "sb-1"
        task.result = result
        return task

    def test_returns_none_when_no_agent_session_key(self) -> None:
        task = self._make_task(result={"sandbox_agent": {"sandbox_id": "x"}})
        assert _task_to_session_record(task) is None

    def test_returns_none_when_result_is_none(self) -> None:
        task = self._make_task(result=None)
        assert _task_to_session_record(task) is None

    def test_builds_record_when_agent_session_present(self) -> None:
        task = self._make_task(
            result={
                _AGENT_SESSION_KEY: {
                    "agent": "opencode",
                    "agent_session_id": "asid-1",
                    "last_connection_id": "conn-1",
                    "destroyed_at": None,
                    "session_init": {"foo": "bar"},
                    "config_options": [],
                    "modes": {},
                }
            }
        )
        rec = _task_to_session_record(task)
        assert rec is not None
        assert rec.id == "task-1"
        assert rec.agent == "opencode"
        assert rec.agent_session_id == "asid-1"
        assert rec.last_connection_id == "conn-1"
        assert rec.sandbox_id == "sb-1"
        assert rec.session_init == {"foo": "bar"}
        assert isinstance(rec.created_at, int)


class TestEventRowToSessionEvent:
    def _make_event(self, *, payload: dict, actor: str, seq: int = 1) -> MagicMock:
        ev = MagicMock()
        ev.id = "ev-1"
        ev.seq = seq
        ev.entity_id = "task-1"
        ev.timestamp = datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc)
        ev.actor = actor
        ev.payload = payload
        return ev

    def test_pulls_connection_id_from_payload(self) -> None:
        ev = self._make_event(
            payload={"connection_id": "conn-9", "text": "hello"},
            actor="agent",
        )
        out = _event_row_to_session_event(ev)
        assert out.connection_id == "conn-9"
        assert out.payload == {"text": "hello"}
        assert "connection_id" not in out.payload

    def test_translates_agent_actor(self) -> None:
        ev = self._make_event(payload={}, actor="agent")
        assert _event_row_to_session_event(ev).sender == "agent"

    def test_translates_user_actor_to_client(self) -> None:
        ev = self._make_event(payload={}, actor=f"user:{uuid4()}")
        assert _event_row_to_session_event(ev).sender == "client"

    def test_uses_seq_as_event_index(self) -> None:
        ev = self._make_event(payload={}, actor="agent", seq=42)
        assert _event_row_to_session_event(ev).event_index == 42

    def test_zero_event_index_when_seq_null(self) -> None:
        ev = self._make_event(payload={}, actor="agent", seq=1)
        ev.seq = None
        assert _event_row_to_session_event(ev).event_index == 0


class TestProtocolSatisfaction:
    def test_driver_class_satisfies_session_persist_driver(self) -> None:
        fake_db = MagicMock()
        driver = OmoiOsSessionPersistDriver(fake_db)
        assert isinstance(driver, SessionPersistDriver)

    def test_default_event_type_is_session_message(self) -> None:
        assert _DEFAULT_EVENT_TYPE == "session.message"

    def test_agent_session_key_is_agent_session(self) -> None:
        # If you change this constant, every existing tasks.result['agent_session']
        # blob in the DB becomes invisible to the adapter. Don't.
        assert _AGENT_SESSION_KEY == "agent_session"
