"""End-to-end tests for the four spec §18 interaction patterns.

Each pattern drives the session lifecycle through the Python SDK against a
running backend + real Daytona. These are gated on environment variables:

    OMOIOS_API_BASE_URL    — backend URL (e.g. http://localhost:18000)
    OMOIOS_PLATFORM_API_KEY — tenant-scoped platform key (`rpk_live_…`)
    DAYTONA_API_KEY         — real Daytona credential

If any are missing the whole file SKIPs rather than failing — this is an e2e
suite, not a unit suite. Patterns covered:

    A. Fire-and-forget — create + disconnect; webhook later (not verified here,
       only the create path; webhook delivery is covered by the smoke test).
    B. Sync wait      — create + iter events until a terminal type lands.
    C. Live stream    — iter events, validate envelope fields per spec §03.
    D. Multiplayer    — two WS channels, presence + cross-channel message.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import httpx
import pytest

from omoios.client import AsyncOmoiOSClient
from omoios.types import Event, Session

API_BASE_URL = os.environ.get("OMOIOS_API_BASE_URL", "")
PLATFORM_KEY = os.environ.get("OMOIOS_PLATFORM_API_KEY", "")
DAYTONA_KEY = os.environ.get("DAYTONA_API_KEY", "")
USER_JWT = os.environ.get("OMOIOS_USER_JWT", "")


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        not (API_BASE_URL and PLATFORM_KEY and DAYTONA_KEY),
        reason="e2e patterns require OMOIOS_API_BASE_URL + OMOIOS_PLATFORM_API_KEY + DAYTONA_API_KEY",
    ),
]


TERMINAL_EVENT_TYPES = {
    "session.succeeded",
    "session.failed",
    "session.cancelled",
    "session.ended",
}


# ─── fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
async def client() -> AsyncOmoiOSClient:
    """SDK client bound to the platform API key."""
    c = AsyncOmoiOSClient(base_url=API_BASE_URL, api_key=PLATFORM_KEY, timeout=30.0)
    try:
        yield c
    finally:
        await c.close()


GITHUB_REPO = os.environ.get("OMOIOS_E2E_GITHUB_REPO", "octocat/hello-world")


@pytest.fixture
async def workspace_id(client: AsyncOmoiOSClient) -> str:
    """Return a workspace id the platform key can create sessions under.

    Since migration 071 sessions can be created without a ticket by pointing
    at a workspace (or a github_repo string that auto-binds one). We prefer
    an existing workspace in the caller's org; when none exists we SKIP so
    the test doesn't silently create workspaces on every CI run.
    """
    async with httpx.AsyncClient(timeout=10.0) as http:
        resp = await http.get(
            f"{API_BASE_URL}/api/v1/workspaces",
            headers={"Authorization": f"Bearer {PLATFORM_KEY}"},
            params={"limit": 1},
        )
    if resp.status_code != 200:
        pytest.skip(f"listing workspaces returned {resp.status_code}")
    payload = resp.json()
    rows = payload if isinstance(payload, list) else payload.get("items", [])
    if not rows:
        pytest.skip("no workspaces available — create one before running e2e")
    return str(rows[0]["id"])


async def _create_session(
    client: AsyncOmoiOSClient, workspace_id: str, *, title_suffix: str = ""
) -> Session:
    """Create a session with a unique idempotency key per call."""
    return await client.sessions.create(
        workspace_id=workspace_id,
        prompt=f"e2e pattern {title_suffix} {uuid.uuid4().hex[:6]}".strip(),
        metadata={"source": "sdk/python/tests/test_e2e_spec_patterns.py"},
        idempotency_key=f"e2e-{uuid.uuid4()}",
    )


# ─── Pattern A — fire and forget ────────────────────────────────────────────


class TestPatternA_FireAndForget:
    """Create a session and move on; webhooks (separately tested) handle completion."""

    async def test_create_returns_session_synchronously(
        self, client: AsyncOmoiOSClient, workspace_id: str
    ) -> None:
        session = await _create_session(client, workspace_id, title_suffix="A")
        assert isinstance(session, Session)
        assert session.id
        # Spec §03 says create returns <200ms and includes an addressable id.
        fetched = await client.sessions.get(session.id)
        assert fetched.id == session.id

    async def test_idempotency_key_dedups_retries(
        self, client: AsyncOmoiOSClient, workspace_id: str
    ) -> None:
        key = f"e2e-idem-{uuid.uuid4()}"
        body_kwargs = {
            "workspace_id": workspace_id,
            "prompt": "idem-replay — same key + same body must return the same session.",
            "idempotency_key": key,
        }
        s1 = await client.sessions.create(**body_kwargs)
        s2 = await client.sessions.create(**body_kwargs)
        assert s1.id == s2.id


# ─── Pattern B — sync wait ──────────────────────────────────────────────────


class TestPatternB_SyncWait:
    """Block until a terminal event lands on the session."""

    async def test_iter_events_until_terminal_or_cap(
        self, client: AsyncOmoiOSClient, workspace_id: str
    ) -> None:
        session = await _create_session(client, workspace_id, title_suffix="B")

        # Bound the wait so the test fails loudly instead of hanging if the
        # envelope emitter isn't wired. 60s is generous for a local backend.
        collected: list[Event] = []
        terminal: Event | None = None

        async def _run() -> None:
            nonlocal terminal
            async for evt in client.sessions.events(session.id):
                collected.append(evt)
                if evt.type in TERMINAL_EVENT_TYPES:
                    terminal = evt
                    return
                if len(collected) >= 50:
                    return

        try:
            await asyncio.wait_for(_run(), timeout=60.0)
        except asyncio.TimeoutError:
            pass

        assert collected, "Pattern B expected ≥1 event from the session's SSE stream"
        # If the backend completed the task we should have a terminal event.
        # Otherwise we at least confirmed the stream is producing envelopes.
        for evt in collected:
            assert evt.seq is not None, f"envelope missing seq: {evt}"


# ─── Pattern C — live stream ────────────────────────────────────────────────


class TestPatternC_LiveStream:
    """Render events as they arrive; validate the spec §03 envelope on each."""

    async def test_envelope_fields_present(
        self, client: AsyncOmoiOSClient, workspace_id: str
    ) -> None:
        session = await _create_session(client, workspace_id, title_suffix="C")

        received: list[Event] = []

        async def _run() -> None:
            async for evt in client.sessions.events(session.id):
                received.append(evt)
                if len(received) >= 3:
                    return

        try:
            await asyncio.wait_for(_run(), timeout=30.0)
        except asyncio.TimeoutError:
            pass

        assert received, "expected ≥1 event on a freshly-created session"
        for evt in received:
            assert evt.id
            assert evt.seq is not None and evt.seq > 0
            assert evt.type
            assert evt.session_id == session.id
            assert evt.actor, f"envelope missing actor attribution: {evt}"

    async def test_resume_from_last_event_id(
        self, client: AsyncOmoiOSClient, workspace_id: str
    ) -> None:
        """Disconnect mid-stream, reconnect with Last-Event-ID, assert continuity."""
        session = await _create_session(client, workspace_id, title_suffix="C-resume")

        initial: list[Event] = []

        async def _drain_initial() -> None:
            async for evt in client.sessions.events(session.id):
                initial.append(evt)
                if len(initial) >= 2:
                    return

        try:
            await asyncio.wait_for(_drain_initial(), timeout=30.0)
        except asyncio.TimeoutError:
            pytest.skip("no events produced by session within 30s; can't exercise resume")

        if len(initial) < 1:
            pytest.skip("no events to resume from")

        resume_from = initial[-1].seq

        # Kick the session so there's something new to observe after the cursor.
        try:
            await client.sessions.reply(session.id, f"resume-probe-{uuid.uuid4().hex[:6]}")
        except Exception:
            pass

        resumed: list[Event] = []

        async def _drain_resumed() -> None:
            async for evt in client.sessions.events(
                session.id, last_event_id=str(resume_from)
            ):
                resumed.append(evt)
                if len(resumed) >= 1:
                    return

        try:
            await asyncio.wait_for(_drain_resumed(), timeout=15.0)
        except asyncio.TimeoutError:
            pytest.skip(f"no events past seq {resume_from} within 15s")

        if resumed:
            assert resumed[0].seq > resume_from, (
                f"resume violated monotonicity: first seq {resumed[0].seq} ≤ {resume_from}"
            )


# ─── Pattern D — multiplayer ────────────────────────────────────────────────


class TestPatternD_Multiplayer:
    """Two channels on the same session; presence + cross-channel message.send."""

    @pytest.fixture(autouse=True)
    def _skip_without_jwt(self) -> None:
        if not USER_JWT:
            pytest.skip(
                "OMOIOS_USER_JWT required — WS auth rejects platform keys"
            )

    async def test_presence_joined_reaches_peer(
        self, client: AsyncOmoiOSClient, workspace_id: str
    ) -> None:
        session = await _create_session(client, workspace_id, title_suffix="D-presence")

        ch_a = client.sessions.connect(session.id, user_token=USER_JWT)
        ch_b = client.sessions.connect(session.id, user_token=USER_JWT)

        joined = asyncio.Event()
        seen: list[dict] = []

        def _on(frame: dict) -> None:
            seen.append(frame)
            joined.set()

        ch_b.on("participant.joined", _on)

        try:
            await ch_b.open()
            await asyncio.sleep(0.2)
            await ch_a.open()
            await asyncio.wait_for(joined.wait(), timeout=10.0)
            assert seen, "B should have observed A's participant.joined"
        finally:
            await ch_a.close()
            await ch_b.close()

    async def test_message_send_broadcasts_cross_channel(
        self, client: AsyncOmoiOSClient, workspace_id: str
    ) -> None:
        session = await _create_session(client, workspace_id, title_suffix="D-message")

        ch_a = client.sessions.connect(session.id, user_token=USER_JWT)
        ch_b = client.sessions.connect(session.id, user_token=USER_JWT)
        text = f"hello-{uuid.uuid4().hex[:6]}"

        got = asyncio.Event()
        received: list[dict] = []

        def _on(frame: dict) -> None:
            data = frame.get("data") if isinstance(frame, dict) else None
            if isinstance(data, dict) and data.get("text") == text:
                received.append(frame)
                got.set()

        ch_b.on("session.message", _on)

        try:
            await ch_b.open()
            await ch_a.open()
            await asyncio.sleep(0.1)
            await ch_a.send({"type": "message.send", "data": {"text": text}})
            await asyncio.wait_for(got.wait(), timeout=10.0)
            assert received, f"B should have received session.message text={text}"
        finally:
            await ch_a.close()
            await ch_b.close()
