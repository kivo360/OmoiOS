"""Connections — user-linked OAuth (spec §18 §2).

V1 surfaces GitHub personal OAuth. LLM keys stay under `credentials`.
"""

from __future__ import annotations

from typing import Any, Dict, List

from omoios.resources.base import BaseResource


class ConnectionsResource(BaseResource):
    """User-linked OAuth provider lifecycle (GitHub only in v1)."""

    async def list(self) -> List[Dict[str, Any]]:
        """List providers the current user has connected."""
        response = await self._client._request("GET", "/api/v1/connections")
        return response.json()

    async def remove(self, provider: str) -> None:
        """Revoke / wipe the stored token for a provider."""
        await self._client._request("DELETE", f"/api/v1/connections/{provider}")

    async def oauth_url(self, provider: str) -> str:
        """Get the URL the user should open to start the OAuth flow.

        The SDK does not handle the callback — the platform's existing
        dashboard callback persists the token. Re-call `list()` after the
        user completes the flow to observe the connection has landed.
        """
        response = await self._client._request(
            "POST", f"/api/v1/connections/{provider}/start"
        )
        return response.json()["oauth_start_url"]
