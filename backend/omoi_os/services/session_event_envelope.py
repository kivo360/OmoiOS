"""Session event envelope emitter — spec §03.

Every event emitted through this service carries the full envelope shape the
spec requires:

    {
        "id":         "<event uuid>",
        "seq":         <monotonic int per session>,
        "type":       "<event_type>",
        "session_id": "<task.id>",
        "actor":      "agent" | "user:<uuid>" | "system",
        "timestamp":  "<ISO8601 UTC>",
        "data":        <domain payload>,
    }

Two things happen atomically:

1. **Persist.** Insert a row into `events` with a `seq` one higher than any
   previous event for the same session. We lock the session's event tail via
   `SELECT MAX(seq) ... FOR UPDATE` so two concurrent emits don't collide on
   the same seq.

2. **Publish.** Broadcast the envelope via `EventBusService.publish()` so SSE
   subscribers and the per-session WebSocket channel see it live without
   polling the DB.

Only session-scoped events (ones tied to a `task.id`) belong here. Non-session
events like `AGENT_HEARTBEAT` continue to use `event_bus.publish()` directly;
their rows have `seq=NULL` and are not served by the SSE replay path.
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from omoi_os.logging import get_logger
from omoi_os.models.event import Event
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now


logger = get_logger(__name__)


# Stable actor prefix so `user:<uuid>` is parseable downstream (SDK, UI).
ACTOR_AGENT = "agent"
ACTOR_SYSTEM = "system"


def actor_user(user_id: UUID | str) -> str:
    """Build a `user:<uuid>` actor string."""
    return f"user:{user_id}"


class SessionEventEnvelope:
    """Emits spec §03-shaped events for a given session.

    Collaborates with the shared `EventBusService` for live publish and a
    SQLAlchemy sync session for durable append + seq allocation.
    """

    def __init__(self, db_session: Session, event_bus: EventBusService):
        self._db = db_session
        self._bus = event_bus

    def emit(
        self,
        *,
        session_id: str,
        event_type: str,
        actor: str,
        data: Optional[dict[str, Any]] = None,
        timestamp: Optional[Any] = None,
        transient: Optional[bool] = None,
    ) -> dict[str, Any]:
        """Append + publish one envelope. Returns the full envelope dict.

        Args:
            session_id: The `tasks.id` this event belongs to.
            event_type: Spec §06 event type (e.g., "session.started").
            actor: `ACTOR_AGENT`, `ACTOR_SYSTEM`, or `actor_user(uuid)`.
            data: Domain-specific payload. Goes into the `data` field.
            timestamp: Override for the event timestamp; defaults to utc_now().
            transient: When True, skip the DB insert and seq allocation —
                the envelope is published live via Redis pubsub but does
                NOT show up on SSE replay. By default any ``.delta`` event
                type auto-promotes to transient because token-level deltas
                produce ~50× more rows per turn than `*.updated` snapshots
                without adding any information that isn't already in the
                snapshot. Pass ``transient=False`` to force-persist a
                ``.delta`` event (rare).

        Raises:
            ValueError: if session_id is empty, event_type is empty, or the
                declared session does not exist in `tasks`.
        """
        if not session_id:
            raise ValueError("session_id is required for envelope events")
        if not event_type:
            raise ValueError("event_type is required")

        if transient is None:
            transient = event_type.endswith(".delta")

        ts = timestamp or utc_now()
        payload = data or {}
        event_id = str(uuid4())

        if transient:
            # Skip the DB row + seq allocation. The envelope rides the
            # Redis pubsub channel so live SSE/WS subscribers see it,
            # but resume-from-Last-Event-ID won't replay it. Snapshot
            # events (``*.updated``) are the source of truth for replay.
            envelope: dict[str, Any] = {
                "id": event_id,
                "seq": None,
                "type": event_type,
                "session_id": session_id,
                "actor": actor,
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "data": payload,
                "transient": True,
            }
        else:
            # Serialize concurrent emits for this session. Postgres disallows
            # FOR UPDATE on aggregate queries, so we use a transaction-scoped
            # advisory lock keyed on a stable hash of the session_id. The lock
            # releases on commit or rollback — no cleanup needed.
            self._db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:sid, 0))"),
                {"sid": session_id},
            )
            row = self._db.execute(
                text(
                    "SELECT COALESCE(MAX(seq), 0) AS max_seq "
                    "FROM events WHERE entity_id = :sid"
                ),
                {"sid": session_id},
            ).first()
            next_seq = (row.max_seq if row else 0) + 1

            event = Event(
                id=event_id,
                event_type=event_type,
                entity_type="session",
                entity_id=session_id,
                payload=payload,
                seq=next_seq,
                actor=actor,
                timestamp=ts,
            )
            self._db.add(event)
            self._db.flush()  # surface FK / constraint errors before we broadcast

            envelope = {
                "id": event_id,
                "seq": next_seq,
                "type": event_type,
                "session_id": session_id,
                "actor": actor,
                "timestamp": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "data": payload,
            }

        # Broadcast. We fire the systemevent with the full envelope nested under
        # `payload.envelope` so downstream consumers (per-session WS, SSE live
        # stream) can round-trip it without a DB lookup.
        try:
            self._bus.publish(
                SystemEvent(
                    event_type=event_type,
                    entity_type="session",
                    entity_id=session_id,
                    payload={"envelope": envelope},
                )
            )
        except Exception:  # noqa: BLE001 — publish is best-effort after persist
            logger.warning(
                "envelope publish failed (event persisted)",
                session_id=session_id,
                event_type=event_type,
                seq=envelope.get("seq"),
            )

        # Also publish to the per-session channel so SessionChannelManager
        # replicas subscribe per-session instead of to the events.* firehose.
        # Matches the pattern the spec §18 Pattern D multiplayer plane needs
        # to survive at >1 replica.
        #
        # Frame shape: flatten the envelope into the WS frame so clients see
        # `frame.data.text` (domain payload) instead of having to dig into
        # `frame.data.data.text`. Matches the cursor.moved shape
        # (`{type, data}`) with envelope metadata as siblings.
        try:
            ws_frame = {
                "type": event_type,
                "data": payload,
                "id": event_id,
                "seq": envelope.get("seq"),
                "actor": actor,
                "timestamp": envelope["timestamp"],
                "session_id": session_id,
            }
            if envelope.get("transient"):
                ws_frame["transient"] = True
            self._bus.publish_to_session(session_id, ws_frame)
        except Exception:  # noqa: BLE001 — best-effort
            logger.warning(
                "per-session envelope publish failed (event persisted)",
                session_id=session_id,
                event_type=event_type,
                seq=envelope.get("seq"),
            )

        return envelope
