"""Unit tests for telemetry callback (Wave 4 T9)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omoios import AsyncOmoiOSClient


@pytest.fixture
def events():
    return []


@pytest.fixture
def client(events):
    return AsyncOmoiOSClient(
        "http://localhost:18000",
        api_key="test-key",
        telemetry=lambda e: events.append(e),
    )


def _mock_ok(payload: dict) -> MagicMock:
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    return r


class TestTelemetry:
    @pytest.mark.asyncio
    async def test_request_and_response_events_fire(self, client, events):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_ok([{"provider": "github"}])
            await client.connections.list()

        kinds = [e["kind"] for e in events]
        assert "request" in kinds
        assert "response" in kinds
        # Response event has status + duration
        response_event = next(e for e in events if e["kind"] == "response")
        assert response_event["status"] == 200
        assert response_event["duration_ms"] >= 0
        # Path is the logical API path, not the full URL
        assert response_event["path"] == "/api/v1/connections"

    @pytest.mark.asyncio
    async def test_error_event_fires_on_network_failure(self, client, events):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = RuntimeError("boom")
            with pytest.raises(RuntimeError):
                await client.connections.list()

        kinds = [e["kind"] for e in events]
        assert "error" in kinds
        err_event = next(e for e in events if e["kind"] == "error")
        assert "RuntimeError" in err_event["error"]

    @pytest.mark.asyncio
    async def test_telemetry_callback_exception_does_not_break_request(self):
        def bad_cb(_event):
            raise RuntimeError("callback boom")

        client = AsyncOmoiOSClient(
            "http://localhost:18000", api_key="test", telemetry=bad_cb
        )
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_ok([])
            rows = await client.connections.list()
            assert rows == []

    @pytest.mark.asyncio
    async def test_no_telemetry_when_callback_is_none(self):
        client = AsyncOmoiOSClient("http://localhost:18000", api_key="test")
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_ok([])
            # No telemetry callback means no code path can go wrong — this
            # is the default for existing callers that haven't opted in.
            await client.connections.list()

    @pytest.mark.asyncio
    async def test_telemetry_does_not_leak_auth_headers(self, client, events):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_ok([])
            await client.connections.list()

        # Every event payload should not contain the api_key or the word
        # "Authorization". Spot-check: serialize to a string and search.
        import json as _json

        serialized = _json.dumps(events)
        assert "test-key" not in serialized
        assert "Authorization" not in serialized
