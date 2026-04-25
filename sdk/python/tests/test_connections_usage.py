"""Unit tests for ConnectionsResource + UsageResource wire formats."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omoios import AsyncOmoiOSClient


@pytest.fixture
def client():
    return AsyncOmoiOSClient("http://localhost:18000", api_key="test-key")


def _mock(payload, status=200):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload
    return r


class TestConnectionsResource:
    @pytest.mark.asyncio
    async def test_list_returns_provider_rows(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock(
                [{"provider": "github", "connected_at": None, "scopes": ["repo"]}]
            )
            rows = await client.connections.list()
        assert rows == [
            {"provider": "github", "connected_at": None, "scopes": ["repo"]}
        ]
        call = mock_req.call_args
        assert call.args[0] == "GET"
        assert "/api/v1/connections" in call.args[1]

    @pytest.mark.asyncio
    async def test_remove_sends_delete(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock(None, status=204)
            await client.connections.remove("github")
        method, url = mock_req.call_args.args[:2]
        assert method == "DELETE"
        assert url.endswith("/api/v1/connections/github")

    @pytest.mark.asyncio
    async def test_oauth_url_returns_platform_url(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock(
                {"oauth_start_url": "https://github.com/login/oauth/authorize?..."}
            )
            url = await client.connections.oauth_url("github")
        assert url.startswith("https://github.com/login/oauth/authorize")


class TestUsageResource:
    @pytest.mark.asyncio
    async def test_current_hits_org_summary_endpoint(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock(
                {
                    "organization_id": "org-1",
                    "subscription_tier": "pro",
                    "workflows_used": 5,
                    "workflows_limit": 100,
                    "free_workflows_remaining": 0,
                    "credit_balance": 10.0,
                    "can_execute": True,
                    "reason": "within-limit",
                }
            )
            body = await client.usage.current()
        assert body["subscription_tier"] == "pro"
        assert mock_req.call_args.args[0] == "GET"
        assert mock_req.call_args.args[1].endswith("/api/v1/usage")

    @pytest.mark.asyncio
    async def test_current_threads_organization_id_param(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock({"workflows_used": 0, "workflows_limit": 0,
                                           "free_workflows_remaining": 0,
                                           "credit_balance": 0.0,
                                           "can_execute": True, "reason": ""})
            await client.usage.current(organization_id="org-abc")
        assert mock_req.call_args.kwargs["params"] == {"organization_id": "org-abc"}

    @pytest.mark.asyncio
    async def test_for_session_hits_per_session_endpoint(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock(
                {
                    "session_id": "sid-1",
                    "compute_seconds": 123.0,
                    "tokens_input": 500,
                    "tokens_output": 250,
                    "total_cost": 0.05,
                }
            )
            body = await client.usage.for_session("sid-1")
        assert body["compute_seconds"] == 123.0
        assert body["tokens_input"] == 500
        assert mock_req.call_args.args[1].endswith("/api/v1/usage/sessions/sid-1")
