"""SessionPersistDriver adapter for sandbox-agent-sdk over omoi_os tables.

Translates the SDK's SessionRecord + SessionEvent objects into reads and writes
on the existing `tasks` and `events` tables — no parallel schema.

Mapping reference (see memory/working-buffer.md for the full table):

    SessionRecord.id                 → tasks.id
    SessionRecord.created_at         → int(tasks.created_at.timestamp())
    SessionRecord.sandbox_id         → tasks.sandbox_id
    SessionRecord.{agent, agent_session_id, last_connection_id, destroyed_at,
                   session_init, config_options, modes}
                                     → tasks.result['agent_session'][...]

    SessionEvent.id                  → events.id
    SessionEvent.event_index         → events.seq
    SessionEvent.session_id          → events.entity_id (entity_type='session')
    SessionEvent.created_at          → int(events.timestamp.timestamp())
    SessionEvent.payload             → events.payload (with connection_id nested)
    SessionEvent.sender              → events.actor (translated)

Sender translation:
    'agent'  ↔ 'agent'
    'client' → 'user:<task.created_by>' (or 'user:<connection_id>' fallback)

Constraint: Task must pre-exist. update_session() raises ValueError if not.
The omoi_os sessions API is responsible for Task creation; the SDK adapter
does not synthesize Task rows because Task has many required fields whose
defaults would be fragile (phase_id, task_type, priority, etc.).

event_index is allocated client-side by the SDK; the adapter writes it
directly as `seq`. Single-Postgres-replica deployment is assumed; multi-replica
SDK clients writing to the same session could race on event_index allocation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm.attributes import flag_modified

from sandboxagent.persistence import DEFAULT_LIST_LIMIT, ListPage
from sandboxagent.types import SessionEvent, SessionRecord

from omoi_os.models.event import Event
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


_AGENT_SESSION_KEY = "agent_session"
_DEFAULT_EVENT_TYPE = "session.message"


def _parse_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        offset = int(cursor)
        return offset if offset >= 0 else 0
    except (ValueError, TypeError):
        return 0


def _to_unix_int(dt: Any) -> int:
    if isinstance(dt, int):
        return dt
    if hasattr(dt, "timestamp"):
        return int(dt.timestamp())
    return 0


def _from_unix_dt(ts: int | None) -> datetime:
    if ts is None:
        return utc_now()
    return datetime.fromtimestamp(ts, tz=timezone.utc)


def _from_unix_iso(ts: int | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _parse_iso_to_unix(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso).timestamp())
    except (ValueError, TypeError):
        return None


def _task_to_session_record(task: Task) -> SessionRecord | None:
    """Build a SessionRecord from a Task, or None if the task isn't SDK-managed."""
    result = task.result or {}
    agent_session = result.get(_AGENT_SESSION_KEY)
    if not agent_session:
        return None
    return SessionRecord(
        id=task.id,
        agent=agent_session.get("agent") or "",
        agent_session_id=agent_session.get("agent_session_id") or "",
        last_connection_id=agent_session.get("last_connection_id") or "",
        created_at=_to_unix_int(task.created_at),
        destroyed_at=_parse_iso_to_unix(agent_session.get("destroyed_at")),
        sandbox_id=task.sandbox_id,
        session_init=agent_session.get("session_init"),
        config_options=agent_session.get("config_options"),
        modes=agent_session.get("modes"),
    )


def _translate_sender(
    sdk_sender: str, *, created_by: UUID | None, connection_id: str
) -> str:
    """SDK sender → omoi_os actor string.

    The chat_responder downstream uses ``actor.startswith("user:")`` to identify
    user turns (services/chat_responder.py:88), so we always emit the colon
    prefix even when falling back to a connection_id.
    """
    if sdk_sender == "agent":
        return "agent"
    if sdk_sender == "client":
        if created_by is not None:
            return f"user:{created_by}"
        return f"user:{connection_id}" if connection_id else "user:anon"
    return sdk_sender


def _untranslate_sender(actor: str) -> str:
    """omoi_os actor → SDK sender."""
    if actor == "agent":
        return "agent"
    if actor.startswith("user:"):
        return "client"
    return actor


def _event_row_to_session_event(ev: Event) -> SessionEvent:
    payload = dict(ev.payload or {})
    connection_id = payload.pop("connection_id", "") or ""
    return SessionEvent(
        id=ev.id,
        event_index=ev.seq or 0,
        session_id=ev.entity_id or "",
        created_at=_to_unix_int(ev.timestamp),
        connection_id=connection_id,
        sender=_untranslate_sender(ev.actor or ""),
        payload=payload,
    )


class OmoiOsSessionPersistDriver:
    """Adapter implementing sandbox-agent-sdk's ``SessionPersistDriver`` over
    omoi_os's existing ``tasks`` + ``events`` tables.

    Satisfies the runtime-checkable ``SessionPersistDriver`` Protocol via duck
    typing — explicit subclassing is unnecessary because ``isinstance`` checks
    against the Protocol succeed when all five async methods are present with
    matching signatures.
    """

    def __init__(self, db: DatabaseService) -> None:
        self._db = db

    async def get_session(self, session_id: str) -> SessionRecord | None:
        async with self._db.get_async_session() as session:
            result = await session.execute(select(Task).where(Task.id == session_id))
            task = result.scalar_one_or_none()
            if task is None:
                return None
            return _task_to_session_record(task)

    async def list_sessions(
        self, *, cursor: str | None = None, limit: int | None = None
    ) -> ListPage[SessionRecord]:
        offset = _parse_cursor(cursor)
        page_limit = limit if (limit and limit > 0) else DEFAULT_LIST_LIMIT
        async with self._db.get_async_session() as session:
            stmt = (
                select(Task)
                .where(Task.result.op("?")(_AGENT_SESSION_KEY))
                .order_by(Task.created_at.asc(), Task.id.asc())
                .limit(page_limit + 1)
                .offset(offset)
            )
            result = await session.execute(stmt)
            tasks = list(result.scalars().all())
            has_more = len(tasks) > page_limit
            page = tasks[:page_limit]
            items: list[SessionRecord] = []
            for t in page:
                rec = _task_to_session_record(t)
                if rec is not None:
                    items.append(rec)
            next_cursor = str(offset + page_limit) if has_more else None
            return ListPage(items=items, next_cursor=next_cursor)

    async def update_session(self, session_record: SessionRecord) -> None:
        async with self._db.get_async_session() as session:
            result = await session.execute(
                select(Task).where(Task.id == session_record.id)
            )
            task = result.scalar_one_or_none()
            if task is None:
                raise ValueError(
                    f"Task not found: {session_record.id}. "
                    "OmoiOsSessionPersistDriver requires the Task to exist "
                    "before update_session is called — create it via the "
                    "omoi_os sessions API first."
                )
            if session_record.sandbox_id is not None:
                task.sandbox_id = session_record.sandbox_id
            existing_result = dict(task.result or {})
            existing_result[_AGENT_SESSION_KEY] = {
                "agent": session_record.agent,
                "agent_session_id": session_record.agent_session_id,
                "last_connection_id": session_record.last_connection_id,
                "destroyed_at": _from_unix_iso(session_record.destroyed_at),
                "session_init": session_record.session_init,
                "config_options": session_record.config_options,
                "modes": session_record.modes,
            }
            task.result = existing_result
            flag_modified(task, "result")
            await session.commit()

    async def list_events(
        self,
        session_id: str,
        *,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> ListPage[SessionEvent]:
        offset = _parse_cursor(cursor)
        page_limit = limit if (limit and limit > 0) else DEFAULT_LIST_LIMIT
        async with self._db.get_async_session() as session:
            stmt = (
                select(Event)
                .where(
                    Event.entity_type == "session",
                    Event.entity_id == session_id,
                    Event.seq.is_not(None),
                )
                .order_by(Event.seq.asc(), Event.id.asc())
                .limit(page_limit + 1)
                .offset(offset)
            )
            result = await session.execute(stmt)
            rows = list(result.scalars().all())
            has_more = len(rows) > page_limit
            items = [_event_row_to_session_event(r) for r in rows[:page_limit]]
            next_cursor = str(offset + page_limit) if has_more else None
            return ListPage(items=items, next_cursor=next_cursor)

    async def insert_event(self, session_id: str, event: SessionEvent) -> None:
        async with self._db.get_async_session() as session:
            created_by_result = await session.execute(
                select(Task.created_by).where(Task.id == session_id)
            )
            created_by = created_by_result.scalar_one_or_none()
            actor = _translate_sender(
                event.sender,
                created_by=created_by,
                connection_id=event.connection_id,
            )
            payload = dict(event.payload or {})
            if event.connection_id:
                payload["connection_id"] = event.connection_id
            ts = _from_unix_dt(event.created_at)
            stmt = pg_insert(Event).values(
                id=event.id,
                event_type=_DEFAULT_EVENT_TYPE,
                entity_type="session",
                entity_id=session_id,
                payload=payload,
                seq=event.event_index,
                actor=actor,
                timestamp=ts,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "payload": stmt.excluded.payload,
                    "seq": stmt.excluded.seq,
                    "actor": stmt.excluded.actor,
                    "timestamp": stmt.excluded.timestamp,
                },
            )
            await session.execute(stmt)
            await session.commit()
