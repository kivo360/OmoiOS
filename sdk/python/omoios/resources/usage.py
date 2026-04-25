"""Usage — spec §18 §2 canonical SDK resource.

Two methods:
  usage.current()           → org-level summary for current billing period
  usage.for_session(sid)    → per-session breakdown (compute_seconds,
                              tokens_input, tokens_output, total_cost)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from omoios.resources.base import BaseResource


class UsageResource(BaseResource):
    """Billing + per-session usage reads (spec §18 §2 `usage`)."""

    async def current(
        self, organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return the current billing-period summary for an org.

        Omit `organization_id` to use the caller's first org membership.
        """
        params: Dict[str, Any] = {}
        if organization_id is not None:
            params["organization_id"] = organization_id
        response = await self._client._request(
            "GET", "/api/v1/usage", params=params or None
        )
        return response.json()

    async def for_session(self, session_id: str) -> Dict[str, Any]:
        """Return compute_seconds + token totals for a single session."""
        response = await self._client._request(
            "GET", f"/api/v1/usage/sessions/{session_id}"
        )
        return response.json()
