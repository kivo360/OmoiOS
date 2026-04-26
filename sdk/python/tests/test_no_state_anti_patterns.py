"""Spec §18 §7 anti-pattern guards: SDK keeps NO state, NO retries.

The SDK must be a thin transport — no client-side caching, no implicit
retry loops. Anything stateful belongs in a separate companion package
(e.g. `@omoios/react`). These tests pin both contracts so future
"helpful" additions can't slip in unnoticed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from omoios import AsyncOmoiOSClient
from omoios.exceptions import ServerError


def _ok(payload: dict) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    return r


def _server_error(payload: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = 503
    r.json.return_value = payload or {"detail": "service unavailable"}
    return r


@pytest.fixture
def client():
    return AsyncOmoiOSClient("http://localhost:18000", api_key="test-key")  # pragma: allowlist secret


class TestNoCaching:
    """Spec §18 §7: GETs are not memoized; each call hits the wire."""

    @pytest.mark.asyncio
    async def test_two_gets_in_a_row_fire_two_requests(self, client):
        session_payload = {"id": "sess_1", "status": "running"}
        with patch.object(
            client._http, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = _ok(session_payload)

            r1 = await client.sessions.get("sess_1")
            r2 = await client.sessions.get("sess_1")

            # Exactly two HTTP calls — no in-memory dedup of identical reads.
            assert mock_req.call_count == 2, (
                f"Expected 2 GET requests; got {mock_req.call_count}. "
                "SDK is caching responses internally — that violates spec §18 §7."
            )
            # Both responses should be parsed independently.
            assert r1.id == "sess_1"
            assert r2.id == "sess_1"

    @pytest.mark.asyncio
    async def test_back_to_back_calls_share_no_observable_state(self, client):
        """Even rapid-fire calls don't share state — the second call must be
        able to observe a different status because we're not caching."""
        first = _ok({"id": "sess_1", "status": "running"})
        second = _ok({"id": "sess_1", "status": "completed"})

        with patch.object(
            client._http, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.side_effect = [first, second]

            r1 = await client.sessions.get("sess_1")
            r2 = await client.sessions.get("sess_1")

            # If a cache existed, r2.status would equal r1.status.
            assert r1.status == "running"
            assert r2.status == "completed"


class TestNoImplicitRetry:
    """Spec §18 §7: a 5xx is surfaced immediately. Retries belong to the caller."""

    @pytest.mark.asyncio
    async def test_503_raises_without_retry(self, client):
        with patch.object(
            client._http, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.return_value = _server_error()

            with pytest.raises(ServerError):
                await client.sessions.get("sess_1")

            # Exactly one attempt — the SDK must not retry transparently.
            assert mock_req.call_count == 1, (
                f"Expected 1 attempt on 503; got {mock_req.call_count}. "
                "SDK is retrying internally — that violates spec §18 §7."
            )

    @pytest.mark.asyncio
    async def test_caller_can_retry_themselves(self, client):
        """The contract: caller wraps and retries. First 503, then 200 succeeds
        when caller drives the retry loop — proving the SDK didn't swallow it."""
        with patch.object(
            client._http, "request", new_callable=AsyncMock
        ) as mock_req:
            mock_req.side_effect = [
                _server_error(),
                _ok({"id": "sess_1", "status": "running"}),
            ]

            with pytest.raises(ServerError):
                await client.sessions.get("sess_1")

            # Caller-driven retry succeeds.
            r = await client.sessions.get("sess_1")
            assert r.id == "sess_1"
            assert mock_req.call_count == 2
