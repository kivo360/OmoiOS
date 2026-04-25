"""Unit tests for SessionsResource.create() wire format."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from omoios import AsyncOmoiOSClient


@pytest.fixture
def client() -> AsyncOmoiOSClient:
    return AsyncOmoiOSClient("http://localhost:18000", api_key="test-key")


def _mock_ok(payload: dict) -> MagicMock:
    r = MagicMock()
    r.status_code = 201
    r.json.return_value = payload
    return r


class TestSessionsCreate:
    """Decoupled create signature — spec §03 shape."""

    @pytest.mark.asyncio
    async def test_create_with_workspace_id_only(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_ok(
                {"id": "t1", "workspace_id": "ws-1", "ticket_id": None}
            )
            session = await client.sessions.create(
                workspace_id="ws-1",
                prompt="hello",
            )
        assert session.id == "t1"
        call = mock_req.call_args
        assert call.kwargs["json"] == {"prompt": "hello", "workspace_id": "ws-1"}
        # Idempotency-Key auto-generated
        assert "Idempotency-Key" in call.kwargs["headers"]

    @pytest.mark.asyncio
    async def test_create_with_github_repo(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_ok(
                {"id": "t2", "github_repo": "octo/hi", "ticket_id": None}
            )
            await client.sessions.create(
                prompt="explore",
                github_repo="octo/hi",
                metadata={"source": "sdk-test"},
            )
        body = mock_req.call_args.kwargs["json"]
        assert body == {
            "prompt": "explore",
            "github_repo": "octo/hi",
            "metadata": {"source": "sdk-test"},
        }

    @pytest.mark.asyncio
    async def test_create_rejects_missing_workspace_and_repo(self, client):
        with pytest.raises(ValueError):
            await client.sessions.create(prompt="hi")

    @pytest.mark.asyncio
    async def test_create_forwards_explicit_idempotency_key(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_ok({"id": "t3", "ticket_id": None})
            await client.sessions.create(
                prompt="p",
                workspace_id="ws",
                idempotency_key="my-key",
            )
        headers = mock_req.call_args.kwargs["headers"]
        assert headers["Idempotency-Key"] == "my-key"

    @pytest.mark.asyncio
    async def test_create_share_with_list_serialised(self, client):
        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_ok({"id": "t4", "ticket_id": None})
            await client.sessions.create(
                prompt="p",
                workspace_id="ws",
                share_with=["user-a", "user-b"],
            )
        body = mock_req.call_args.kwargs["json"]
        assert body["share_with"] == ["user-a", "user-b"]
