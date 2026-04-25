"""Sessions resource — spec §03 primary SDK surface.

Methods mirror the backend's `/api/v1/sessions/*` routes one-to-one:

    client.sessions.create(...)            POST   /api/v1/sessions
    client.sessions.get(id)                GET    /api/v1/sessions/{id}
    client.sessions.list(...)              GET    /api/v1/sessions   (auto-paginate)
    client.sessions.cancel(id)             DELETE /api/v1/sessions/{id}
    client.sessions.reply(id, text)        POST   /api/v1/sessions/{id}/messages
    client.sessions.fork(id, seq, prompt)  POST   /api/v1/sessions/{id}/fork
    client.sessions.share(id, grants)      POST   /api/v1/sessions/{id}/share
    client.sessions.artifacts(id)          GET    /api/v1/sessions/{id}/artifacts
    client.sessions.events(id, ...)        GET    /api/v1/sessions/{id}/events   (SSE)
    client.sessions.connect(id, token)     WS     /api/v1/sessions/{id}/ws

Four primitive interaction patterns from spec §18 are all expressible here:

    A. Fire-and-forget:  s = await client.sessions.create(...)
    B. Sync wait:        async for e in client.sessions.events(s.id): ...
    C. Live stream:      same as B, render each event as it arrives
    D. Multiplayer:      ch = client.sessions.connect(s.id, jwt); ch.on(...)
"""

from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional
from urllib.parse import urljoin

from omoios.resources.base import BaseResource
from omoios.types import (
    Artifact,
    Event,
    Grant,
    Session,
)


class SessionsResource(BaseResource):
    """Session lifecycle + streaming (spec §03, §07, §18)."""

    # ─── core lifecycle ─────────────────────────────────────────────────────

    async def create(
        self,
        *,
        prompt: str,
        workspace_id: Optional[str] = None,
        environment_id: Optional[str] = None,
        github_repo: Optional[str] = None,
        share_with: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        cancel_scope: Optional[Any] = None,
    ) -> Session:
        """Create a new session (spec §03).

        Either `workspace_id` or `github_repo` must be supplied. When only
        `github_repo="owner/repo"` is given, the backend auto-binds a
        workspace to that repo within the caller's org (mirrors the ticket
        auto-project behaviour on the dashboard side).

        `idempotency_key` is auto-generated if omitted; pass your own to dedup
        retries across network failures. Same key + same body = same session.
        """
        if not workspace_id and not github_repo:
            raise ValueError("Provide either `workspace_id` or `github_repo`")

        body: Dict[str, Any] = {"prompt": prompt}
        if workspace_id is not None:
            body["workspace_id"] = workspace_id
        if environment_id is not None:
            body["environment_id"] = environment_id
        if github_repo is not None:
            body["github_repo"] = github_repo
        if share_with:
            body["share_with"] = list(share_with)
        if metadata is not None:
            body["metadata"] = metadata

        headers = {
            "Idempotency-Key": idempotency_key or str(uuid.uuid4()),
        }
        response = await self._client._request(
            "POST",
            "/api/v1/sessions",
            json=body,
            headers=headers,
            cancel_scope=cancel_scope,
        )
        return Session(**response.json())

    async def get(
        self,
        session_id: str,
        *,
        cancel_scope: Optional[Any] = None,
    ) -> Session:
        """Fetch a session by id."""
        response = await self._client._request(
            "GET",
            f"/api/v1/sessions/{session_id}",
            cancel_scope=cancel_scope,
        )
        return Session(**response.json())

    async def list(
        self,
        *,
        status: Optional[str] = None,
        phase_id: Optional[str] = None,
        ticket_id: Optional[str] = None,
        page_size: int = 100,
        cancel_scope: Optional[Any] = None,
    ) -> AsyncIterator[Session]:
        """List sessions with auto-pagination (spec §09).

        Yields sessions one at a time. Under the hood this pages using the
        backend's `limit`/`offset` params. For the eager `list[Session]`
        shape, use `list_all()` instead.
        """
        offset = 0
        while True:
            params: Dict[str, Any] = {"limit": page_size, "offset": offset}
            if status is not None:
                params["status"] = status
            if phase_id is not None:
                params["phase_id"] = phase_id
            if ticket_id is not None:
                params["ticket_id"] = ticket_id

            response = await self._client._request(
                "GET",
                "/api/v1/sessions",
                params=params,
                cancel_scope=cancel_scope,
            )
            items = response.json()
            if not isinstance(items, list):
                items = items.get("items", [])

            for item in items:
                yield Session(**item)

            if len(items) < page_size:
                return
            offset += page_size

    async def list_all(self, **kwargs: Any) -> List[Session]:
        """Eager variant of `list()` — collects all pages into a list."""
        return [s async for s in self.list(**kwargs)]

    async def cancel(
        self,
        session_id: str,
        *,
        cancel_scope: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Cancel a running session. Idempotent."""
        response = await self._client._request(
            "DELETE",
            f"/api/v1/sessions/{session_id}",
            cancel_scope=cancel_scope,
        )
        return response.json()

    # ─── spec §03 lifecycle actions ─────────────────────────────────────────

    async def reply(
        self,
        session_id: str,
        text: str,
        *,
        cancel_scope: Optional[Any] = None,
    ) -> None:
        """Send a follow-up prompt mid-session. Non-blocking."""
        await self._client._request(
            "POST",
            f"/api/v1/sessions/{session_id}/messages",
            json={"text": text},
            cancel_scope=cancel_scope,
        )

    async def fork(
        self,
        session_id: str,
        from_seq: int,
        prompt: str,
        *,
        cancel_scope: Optional[Any] = None,
    ) -> Session:
        """Branch a session at event `from_seq` with a new prompt."""
        response = await self._client._request(
            "POST",
            f"/api/v1/sessions/{session_id}/fork",
            json={"from_seq": from_seq, "prompt": prompt},
            cancel_scope=cancel_scope,
        )
        return Session(**response.json())

    async def share(
        self,
        session_id: str,
        grants: List[Grant],
        *,
        cancel_scope: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Grant ACL roles on a session (spec §07)."""
        body = {
            "grants": [
                {"user_id": str(g.user_id), "role": g.role} for g in grants
            ]
        }
        response = await self._client._request(
            "POST",
            f"/api/v1/sessions/{session_id}/share",
            json=body,
            cancel_scope=cancel_scope,
        )
        return response.json()

    async def artifacts(
        self,
        session_id: str,
        *,
        cancel_scope: Optional[Any] = None,
    ) -> List[Artifact]:
        """List artifacts produced by this session."""
        response = await self._client._request(
            "GET",
            f"/api/v1/sessions/{session_id}/artifacts",
            cancel_scope=cancel_scope,
        )
        rows = response.json()
        return [Artifact(**row) for row in rows]

    # ─── spec §03 streaming ─────────────────────────────────────────────────

    async def events(
        self,
        session_id: str,
        *,
        last_event_id: Optional[str] = None,
    ) -> AsyncIterator[Event]:
        """Stream session events as a native async iterator.

        Uses `httpx-sse` under the hood — robust SSE framing, `Last-Event-ID`
        header for resume. The iterator closes cleanly when the server
        finishes (replay exhausted + no Redis) or when the caller breaks
        out of the loop.

        Example (spec §18 Pattern B — sync wait):

            async for evt in client.sessions.events(session_id):
                if evt.type == "session.succeeded":
                    break
        """
        # Import here so the SDK imports cleanly even when httpx-sse is
        # absent — callers only pay the dependency when they stream events.
        try:
            from httpx_sse import aconnect_sse
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "Streaming events requires `httpx-sse`. "
                "Install with `pip install omoios[sse]` or "
                "`pip install httpx-sse`."
            ) from exc

        headers = {
            **self._client._headers(),
            "Accept": "text/event-stream",
        }
        if last_event_id:
            headers["Last-Event-ID"] = last_event_id

        url = urljoin(
            self._client.base_url + "/",
            f"api/v1/sessions/{session_id}/events",
        )

        import time

        stream_path = f"/api/v1/sessions/{session_id}/events"
        self._client._emit_telemetry(
            {"kind": "stream_open", "path": stream_path}
        )
        started = time.perf_counter()
        frames = 0
        try:
            async with aconnect_sse(
                self._client._http, "GET", url, headers=headers
            ) as es:
                async for sse in es.aiter_sse():
                    if not sse.data:
                        continue
                    try:
                        payload = json.loads(sse.data)
                    except (ValueError, TypeError):
                        continue
                    frames += 1
                    yield Event(**payload)
        finally:
            self._client._emit_telemetry(
                {
                    "kind": "stream_close",
                    "path": stream_path,
                    "frames_received": frames,
                    "duration_ms": (time.perf_counter() - started) * 1000,
                }
            )

    def connect(
        self, session_id: str, user_token: Optional[str] = None
    ) -> "SessionChannel":
        """Open a multiplayer WebSocket channel (spec §07).

        `user_token` defaults to the client's active JWT; pass a different
        one for a delegated session.
        """
        token = user_token or self._client.jwt_token or self._client.api_key
        return SessionChannel(
            client=self._client, session_id=session_id, token=token or ""
        )


# ─── multiplayer channel ────────────────────────────────────────────────────


class SessionChannel:
    """Thin wrapper around a per-session WebSocket (spec §07).

    Usage:

        ch = client.sessions.connect(session_id, user_jwt)
        ch.on("participant.joined", on_join)
        ch.on("session.message", on_msg)
        await ch.open()
        await ch.send({"type": "message.send", "data": {"text": "hi"}})
        await ch.close()

    Or as an async context manager:

        async with client.sessions.connect(session_id, jwt) as ch:
            ch.on("*", print)
            await asyncio.sleep(30)
    """

    def __init__(self, *, client, session_id: str, token: str):
        self._client = client
        self._session_id = session_id
        self._token = token
        self._ws = None
        self._ws_ctx = None  # httpx-ws async-context-manager handle
        self._reader_task = None
        self._handlers: Dict[str, List[Callable[[Dict[str, Any]], Any]]] = {}
        self._star_handlers: List[Callable[[Dict[str, Any]], Any]] = []

    # ── event subscriptions ────────────────────────────────────────────────

    def on(
        self,
        event_type: str,
        fn: Callable[[Dict[str, Any]], Any],
    ) -> None:
        """Register a handler for a message type. Use `"*"` to catch all."""
        if event_type == "*":
            self._star_handlers.append(fn)
        else:
            self._handlers.setdefault(event_type, []).append(fn)

    # ── lifecycle ─────────────────────────────────────────────────────────

    async def open(self) -> "SessionChannel":
        """Connect the WebSocket and start the read loop.

        Uses `httpx-ws` so the channel rides on the same httpx transport as
        the rest of the SDK — shared connection pool, shared timeouts, and
        the same auth-header plumbing. No separate `websockets` dependency.
        """
        import asyncio

        try:
            from httpx_ws import aconnect_ws
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "WebSocket multiplayer requires `httpx-ws`. "
                "Install with `pip install omoios[ws]` or "
                "`pip install httpx-ws`."
            ) from exc

        # Build ws:// or wss:// URL from the client's base URL.
        base = self._client.base_url
        ws_scheme = "wss" if base.startswith("https") else "ws"
        url = (
            f"{ws_scheme}://{base.split('://', 1)[1]}"
            f"/api/v1/sessions/{self._session_id}/ws"
            f"?token={self._token}"
        )

        # `aconnect_ws` returns an async context manager. Enter it manually
        # so the socket stays open for the lifetime of this channel; we
        # release in `close()`.
        self._ws_ctx = aconnect_ws(url, self._client._http)
        self._ws = await self._ws_ctx.__aenter__()
        self._reader_task = asyncio.create_task(self._read_loop())
        self._client._emit_telemetry(
            {
                "kind": "stream_open",
                "path": f"/api/v1/sessions/{self._session_id}/ws",
            }
        )
        import time as _time
        self._opened_at = _time.perf_counter()
        self._frames_received = 0
        return self

    async def send(self, message: Dict[str, Any]) -> None:
        """Send one message frame (spec §07 shapes: message.send, cursor.moved)."""
        if self._ws is None:
            raise RuntimeError("Channel is not open; call .open() first")
        await self._ws.send_text(json.dumps(message))

    async def close(self) -> None:
        """Close the WebSocket and tear down the reader task."""
        import asyncio as _asyncio

        # Cancel the reader first so it doesn't try to read from a closed
        # socket during teardown. CancelledError is a BaseException in
        # Python 3.8+, not Exception — catch both so the cancel doesn't
        # bubble out of close().
        if self._reader_task is not None:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except (_asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._reader_task = None

        if self._ws is not None and self._ws_ctx is not None:
            try:
                await self._ws_ctx.__aexit__(None, None, None)
            except (_asyncio.CancelledError, Exception):  # noqa: BLE001
                pass
            self._ws = None
            self._ws_ctx = None

        # Telemetry close — fires once per channel regardless of how we
        # got here (explicit close or context-manager exit).
        if getattr(self, "_opened_at", None) is not None:
            import time as _time
            self._client._emit_telemetry(
                {
                    "kind": "stream_close",
                    "path": f"/api/v1/sessions/{self._session_id}/ws",
                    "frames_received": getattr(self, "_frames_received", 0),
                    "duration_ms": (_time.perf_counter() - self._opened_at) * 1000,
                }
            )
            self._opened_at = None

    async def __aenter__(self) -> "SessionChannel":
        return await self.open()

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    # ── internals ──────────────────────────────────────────────────────────

    async def _read_loop(self) -> None:
        """Dispatch inbound frames to registered handlers."""
        assert self._ws is not None
        try:
            while True:
                raw = await self._ws.receive_text()
                try:
                    frame = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                self._frames_received = getattr(self, "_frames_received", 0) + 1
                # Fire star handlers regardless of shape.
                for handler in self._star_handlers:
                    _maybe_await(handler, frame)
                # Fire type-specific handlers if the frame has a type field.
                msg_type = frame.get("type")
                if msg_type:
                    for handler in self._handlers.get(msg_type, []):
                        _maybe_await(handler, frame)
        except Exception:  # noqa: BLE001 — socket closed or transport error
            return


def _maybe_await(fn: Callable[[Any], Any], arg: Any) -> None:
    """Call `fn(arg)`. If it returns a coroutine, schedule it on the loop."""
    import asyncio

    result = fn(arg)
    if hasattr(result, "__await__"):
        asyncio.create_task(result)  # type: ignore[arg-type]
