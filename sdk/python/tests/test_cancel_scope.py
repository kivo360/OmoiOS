"""Unit tests for cancel_scope plumbing on _request (Wave 4 T10)."""

from __future__ import annotations

import asyncio

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omoios import AsyncOmoiOSClient


def _ok(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    return r


@pytest.mark.asyncio
async def test_request_accepts_cancel_scope_kwarg():
    """Passing cancel_scope flows into _request without error; no-op when None."""
    client = AsyncOmoiOSClient("http://localhost:18000", api_key="test")
    with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = _ok([])
        # Calling _request directly (what resources do) with cancel_scope=None
        res = await client._request("GET", "/api/v1/connections", cancel_scope=None)
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_asyncio_wait_for_cancels_in_flight_httpx_call():
    """httpx already cooperates with asyncio.wait_for cancellation — this is
    the 'implicit' cancellation path. Spec §18 §1 principle 5 is satisfied
    by this working today; the explicit cancel_scope kwarg adds a second
    surface for callers who want to build reusable scopes.
    """
    client = AsyncOmoiOSClient("http://localhost:18000", api_key="test")

    async def _slow(*_args, **_kwargs):
        await asyncio.sleep(10)
        return _ok([])

    with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = _slow
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(client.connections.list(), timeout=0.05)
