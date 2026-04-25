"""Per-session multiplayer WebSocket channel — spec §07.

Separate module from the global `/ws/events` firehose so the broadcast group
is properly session-scoped. Every socket joined to a session receives:

- Envelope-shaped events emitted for that session (from the event bus)
- `participant.joined` / `participant.left` presence updates
- Messages and cursor moves sent by other participants

Inbound client messages are shaped per spec §18:

    {"type": "message.send", "data": {"text": "…"}}
    {"type": "cursor.moved",  "data": {"file": "foo.ts", "line": 42}}

`message.send` is persisted through the envelope service (so it also shows
up in the SSE stream and in DB replay). `cursor.moved` is ephemeral — it
broadcasts to peers and is never written to `events`.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional
from uuid import UUID

from fastapi import Query, WebSocket, WebSocketDisconnect

from omoi_os.logging import get_logger
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.session_event_envelope import SessionEventEnvelope, actor_user


logger = get_logger(__name__)


class SessionChannelManager:
    """Tracks live WebSocket connections grouped by session_id.

    One manager instance is shared across the process via a module-level
    singleton. Each registered socket carries its resolved `user_id` so we
    can emit participant events without the caller having to re-auth.
    """

    def __init__(self) -> None:
        # session_id → list of (websocket, user_id). Kept as a list (not set)
        # because the same user can hold multiple sockets (web + extension).
        # `_rooms` is a local replica cache — NOT the source of truth for
        # which replica holds a given session. Redis ch.{session_id} is.
        self._rooms: dict[str, list[tuple[WebSocket, UUID]]] = {}
        self._lock = asyncio.Lock()
        self._bus_task: Optional[asyncio.Task[None]] = None
        self._bus_pubsub: Any = None
        self._bus: Optional[EventBusService] = None
        # Track which per-session channels this replica is subscribed to so
        # we can unsubscribe cleanly when the last local participant leaves.
        self._subscribed_sessions: set[str] = set()

    async def join(self, session_id: str, ws: WebSocket, user_id: UUID) -> None:
        """Register a new socket on a session and broadcast presence."""
        async with self._lock:
            first_on_replica = session_id not in self._rooms
            self._rooms.setdefault(session_id, []).append((ws, user_id))

        # First local participant for this session on this replica → subscribe
        # to its per-session Redis channel so envelopes + cursor.moved from
        # other replicas fan out here.
        if first_on_replica:
            await self._subscribe_session(session_id)

        await self._broadcast_to(
            session_id,
            {"type": "participant.joined", "data": {"user_id": str(user_id)}},
            exclude=ws,
        )

    async def leave(self, session_id: str, ws: WebSocket, user_id: UUID) -> None:
        """Unregister a socket and broadcast the departure."""
        async with self._lock:
            members = self._rooms.get(session_id, [])
            self._rooms[session_id] = [(s, uid) for (s, uid) in members if s is not ws]
            empty = not self._rooms[session_id]
            if empty:
                self._rooms.pop(session_id, None)

        await self._broadcast_to(
            session_id,
            {"type": "participant.left", "data": {"user_id": str(user_id)}},
            exclude=None,
        )

        # Last local participant dropped → release the per-session subscription.
        if empty:
            await self._unsubscribe_session(session_id)

    async def broadcast(
        self,
        session_id: str,
        message: dict[str, Any],
        exclude: Optional[WebSocket] = None,
    ) -> None:
        """Public entrypoint used by the event-bus bridge."""
        await self._broadcast_to(session_id, message, exclude=exclude)

    async def _broadcast_to(
        self,
        session_id: str,
        message: dict[str, Any],
        exclude: Optional[WebSocket],
    ) -> None:
        async with self._lock:
            members = list(self._rooms.get(session_id, []))
        dead: list[WebSocket] = []
        for sock, _uid in members:
            if sock is exclude:
                continue
            try:
                await sock.send_json(message)
            except Exception as e:  # noqa: BLE001 — socket errors are expected on disconnect
                logger.debug("ws send failed", error=str(e))
                dead.append(sock)

        if dead:
            async with self._lock:
                for sid, roster in list(self._rooms.items()):
                    self._rooms[sid] = [(s, u) for (s, u) in roster if s not in dead]
                    if not self._rooms[sid]:
                        self._rooms.pop(sid, None)

    async def ensure_bus_bridge(self, bus: EventBusService) -> None:
        """Start the Redis→per-session bridge task once per process.

        The bridge subscribes to `ch.{session_id}` channels — one per
        session that has at least one local participant. `SessionEventEnvelope`
        publishes every frame to both the legacy `events.{event_type}`
        firehose AND `ch.{session_id}`, and `cursor.moved` publishes only
        to `ch.{session_id}`. The bridge fans out inbound messages to every
        local socket in the matching room.

        This replaces the legacy `psubscribe("events.*")` firehose, which
        meant every replica received every session's events and filtered
        in Python. Per-session channels let Redis do the filtering so we
        scale with `active sessions × replicas holding ≥1 participant`,
        not `all sessions × all replicas`.
        """
        if self._bus_task and not self._bus_task.done():
            return
        if not getattr(bus, "_available", False) or not bus.redis_client:
            return
        self._bus = bus
        self._bus_pubsub = bus.redis_client.pubsub()
        self._bus_task = asyncio.create_task(self._bridge_loop())

    async def _subscribe_session(self, session_id: str) -> None:
        """Subscribe this replica's shared PubSub to ch.{session_id}."""
        if self._bus_pubsub is None:
            return
        if session_id in self._subscribed_sessions:
            return
        loop = asyncio.get_event_loop()
        channel = f"ch.{session_id}"
        try:
            await loop.run_in_executor(
                None, lambda: self._bus_pubsub.subscribe(channel)
            )
            self._subscribed_sessions.add(session_id)
        except Exception:  # noqa: BLE001
            logger.exception("subscribe failed", extra={"session_id": session_id})

    async def _unsubscribe_session(self, session_id: str) -> None:
        """Release the ch.{session_id} subscription when roster hits 0."""
        if self._bus_pubsub is None:
            return
        if session_id not in self._subscribed_sessions:
            return
        loop = asyncio.get_event_loop()
        channel = f"ch.{session_id}"
        try:
            await loop.run_in_executor(
                None, lambda: self._bus_pubsub.unsubscribe(channel)
            )
            self._subscribed_sessions.discard(session_id)
        except Exception:  # noqa: BLE001
            logger.exception("unsubscribe failed", extra={"session_id": session_id})

    async def _bridge_loop(self) -> None:
        loop = asyncio.get_event_loop()
        try:
            while True:
                message = await loop.run_in_executor(
                    None,
                    lambda: self._bus_pubsub.get_message(
                        ignore_subscribe_messages=True, timeout=1.0
                    ),
                )
                if not message or message.get("type") != "message":
                    continue
                channel = message.get("channel", "")
                if not channel.startswith("ch."):
                    continue
                sid = channel[len("ch.") :]
                try:
                    frame = json.loads(message["data"])
                except (ValueError, TypeError):
                    continue
                # Frames coming through ch.{sid} are already full WS shapes:
                # {type: "cursor.moved"|"session.message"|..., data: {...}}
                if not isinstance(frame, dict):
                    continue
                await self._broadcast_to(sid, frame, exclude=None)
        except asyncio.CancelledError:
            pass
        except Exception:  # noqa: BLE001
            logger.exception("session channel bridge crashed")


_manager: Optional[SessionChannelManager] = None


def get_session_channel_manager() -> SessionChannelManager:
    """Lazily construct the process-wide channel manager."""
    global _manager
    if _manager is None:
        _manager = SessionChannelManager()
    return _manager


async def _authenticate_ws_token(token: str):
    """Resolve a JWT to a User. Returns the user or None.

    Shares the pattern used by `routes/events.py::_authenticate_websocket`,
    but returns the user instead of closing the socket directly so the
    caller can decide whether to send a structured error envelope first.
    """
    if not token:
        return None
    try:
        from omoi_os.api.dependencies import get_db_service
        from omoi_os.config import settings
        from omoi_os.services.auth_service import AuthService

        db = get_db_service()
        with db.get_session() as session:
            auth_service = AuthService(
                db=session,
                jwt_secret=settings.jwt_secret_key,
                jwt_algorithm=settings.jwt_algorithm,
                access_token_expire_minutes=settings.access_token_expire_minutes,
                refresh_token_expire_days=settings.refresh_token_expire_days,
            )
            token_data = auth_service.verify_token(token, token_type="access")
            if not token_data:
                return None
            from omoi_os.models.user import User

            user = session.get(User, token_data.user_id)
            if user:
                session.expunge(user)
            return user
    except Exception:  # noqa: BLE001
        logger.exception("ws auth failed")
        return None


async def session_ws_endpoint(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None, description="JWT access token"),
) -> None:
    """Per-session multiplayer WebSocket (spec §07).

    This function is registered as a FastAPI websocket route from the
    sessions router. It stays small — all stateful work lives in
    `SessionChannelManager`.
    """
    user = await _authenticate_ws_token(token or "")
    if user is None:
        await websocket.accept()
        await websocket.send_json({"error": "Authentication required"})
        await websocket.close(code=4401)
        return

    # Session access check: reuse the dependency as a plain callable.
    from omoi_os.api.dependencies import get_db_service

    db = get_db_service()
    try:
        # Use the module-level reference so tests can monkeypatch it.
        import omoi_os.api.routes.session_channel as _self_mod

        await _self_mod.verify_task_access(session_id, user, db)
    except Exception as _exc:  # noqa: BLE001 — HTTPException or missing-row
        # Log the actual error so 4403s aren't a black box. Distinguish a
        # genuine permission denial (HTTPException 403/404) from an unexpected
        # crash inside the access check.
        from fastapi import HTTPException as _H

        if isinstance(_exc, _H):
            logger.info(
                "ws session access denied",
                session_id=session_id,
                user_id=str(user.id),
                status_code=_exc.status_code,
                detail=str(_exc.detail),
            )
        else:
            logger.exception(
                "ws session access check crashed (treated as forbidden)",
                session_id=session_id,
                user_id=str(user.id),
                exc_type=type(_exc).__name__,
            )
        await websocket.accept()
        await websocket.send_json({"error": "Forbidden"})
        await websocket.close(code=4403)
        return

    await websocket.accept()

    manager = get_session_channel_manager()
    # Bridge Redis→channel once per process; safe to call on every join.
    from omoi_os.api.dependencies import get_event_bus_service

    bus = get_event_bus_service()
    await manager.ensure_bus_bridge(bus)

    await manager.join(session_id, websocket, user.id)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (ValueError, TypeError):
                await websocket.send_json({"error": "Invalid JSON"})
                continue

            msg_type = msg.get("type")
            data = msg.get("data") or {}

            if msg_type == "message.send":
                text = (data.get("text") or "").strip()
                if not text:
                    await websocket.send_json(
                        {"error": "message.send requires non-empty data.text"}
                    )
                    continue
                # Persist via envelope so SSE + DB replay see it.
                with db.get_session() as session:
                    envelope = SessionEventEnvelope(session, bus)
                    env = envelope.emit(
                        session_id=session_id,
                        event_type="session.message",
                        actor=actor_user(user.id),
                        data={"text": text},
                    )
                    session.commit()
                # The envelope publish fans out through the bus bridge to
                # every socket; no extra broadcast needed here.
                # Send an ack to the sender so clients can show delivery.
                await websocket.send_json(
                    {"type": "message.ack", "data": {"seq": env["seq"]}}
                )
                continue

            if msg_type == "cursor.moved":
                # Route through Redis `ch.{session_id}` so replicas holding
                # other participants of this session (possibly behind a
                # different LB-targeted uvicorn process) see the event.
                # Every replica's bridge loop rebroadcasts to its local
                # sockets; the sender receives its own echo and filters it
                # client-side via user_id. (Local-only direct broadcast was
                # the pre-spec-18 behaviour and fragmented at >1 replica.)
                frame = {
                    "type": "cursor.moved",
                    "data": {**data, "user_id": str(user.id)},
                }
                bus.publish_to_session(session_id, frame)
                continue

            await websocket.send_json({"error": f"Unknown message type: {msg_type}"})
    except WebSocketDisconnect:
        pass
    finally:
        await manager.leave(session_id, websocket, user.id)
