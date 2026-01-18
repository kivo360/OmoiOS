"""HTTP reporter for production (Daytona sandboxes).

POSTs events to the backend sandbox events API endpoint:
  POST /api/v1/sandboxes/{sandbox_id}/events

This is the callback mechanism for spec-sandbox to report progress
to the backend. Events are persisted to the sandbox_events table
and used to update spec phase_data.

Includes SyncSummary-style reporting for traceability statistics.
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event


class HTTPReporter(Reporter):
    """POSTs events to backend sandbox events API (production mode).

    Events are sent to: POST /api/v1/sandboxes/{sandbox_id}/events

    The backend expects each event to have:
    - event_type: str (e.g., "phase.started", "spec.completed")
    - event_data: dict with optional spec_id for spec-driven development
    - source: str ("agent", "worker", "system")

    Features:
    - Batching: Collects events and sends in batches
    - Retry: Retries failed requests with exponential backoff
    - Timeout: Configurable request timeout
    - SyncSummary: Final spec summary with traceability stats
    - spec_id injection: Automatically adds spec_id to event_data

    Usage:
        reporter = HTTPReporter(
            callback_url="https://api.omoios.dev",
            sandbox_id="daytona-sandbox-123",
            spec_id="spec-uuid-456",
        )
        machine = SpecStateMachine(reporter=reporter, ...)
        await machine.run()
    """

    def __init__(
        self,
        callback_url: str,
        sandbox_id: str,
        spec_id: Optional[str] = None,
        api_key: Optional[str] = None,
        batch_size: int = 10,
        flush_interval: float = 5.0,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.callback_url = callback_url.rstrip("/")
        self.sandbox_id = sandbox_id
        self.spec_id = spec_id
        self.api_key = api_key
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.timeout = timeout
        self.max_retries = max_retries

        self._buffer: List[Event] = []
        self._client: Optional[httpx.AsyncClient] = None
        self._sync_summary: Optional[Dict[str, Any]] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with authentication."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=headers,
            )
        return self._client

    async def report(self, event: Event) -> None:
        """Add event to buffer, flush if batch size reached."""
        self._buffer.append(event)

        if len(self._buffer) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Send buffered events to sandbox events endpoint.

        Events are sent one-by-one to:
          POST /api/v1/sandboxes/{sandbox_id}/events

        Each event includes spec_id in event_data for spec-driven development.
        """
        if not self._buffer:
            return

        events_to_send = self._buffer.copy()
        self._buffer.clear()

        client = await self._get_client()
        endpoint = f"{self.callback_url}/api/v1/sandboxes/{self.sandbox_id}/events"

        for event in events_to_send:
            # Build event payload matching backend's SandboxEventCreate schema
            event_data = event.data or {}
            # Inject spec_id into event_data for spec-driven development tracking
            if self.spec_id:
                event_data["spec_id"] = self.spec_id

            payload = {
                "event_type": event.event_type,
                "event_data": event_data,
                "source": "agent",
            }

            for attempt in range(self.max_retries):
                try:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                    break  # Success, move to next event
                except httpx.HTTPError as e:
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(2**attempt)  # Exponential backoff
                    else:
                        # On final failure, log but don't crash
                        # Events are lost but execution continues
                        print(
                            f"Failed to send event {event.event_type} after {self.max_retries} attempts: {e}"
                        )

    async def report_sync_summary(
        self,
        spec_id: str,
        sync_output: Dict[str, Any],
        phase_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Report the final sync summary with traceability statistics.

        This sends an agent.completed event with phase_data, which the backend
        uses to update the spec's phase_data via _update_spec_phase_data().

        Args:
            spec_id: The spec identifier
            sync_output: The sync phase output with traceability_stats
            phase_data: Optional additional phase data to include
        """
        # Build SyncSummary-style payload
        traceability_stats = sync_output.get("traceability_stats", {})
        spec_summary = sync_output.get("spec_summary", {})
        validation_results = sync_output.get("validation_results", {})

        summary_payload = {
            "spec_id": spec_id,
            "status": "completed" if sync_output.get("ready_for_execution") else "blocked",
            "traceability": {
                "requirements": traceability_stats.get("requirements", {}),
                "tasks": traceability_stats.get("tasks", {}),
                "orphans": traceability_stats.get("orphans", {}),
            },
            "validation": {
                "all_requirements_covered": validation_results.get("all_requirements_covered", False),
                "all_components_have_tasks": validation_results.get("all_components_have_tasks", False),
                "dependency_order_valid": validation_results.get("dependency_order_valid", False),
                "no_circular_dependencies": validation_results.get("no_circular_dependencies", False),
                "issues": validation_results.get("issues_found", []),
            },
            "summary": {
                "total_requirements": spec_summary.get("total_requirements", 0),
                "total_tasks": spec_summary.get("total_tasks", 0),
                "total_estimated_hours": spec_summary.get("total_estimated_hours", 0),
                "files_to_modify": spec_summary.get("files_to_modify", 0),
                "files_to_create": spec_summary.get("files_to_create", 0),
                "requirement_coverage_percent": spec_summary.get("requirement_coverage_percent", 0.0),
            },
            "coverage_matrix": sync_output.get("coverage_matrix", []),
            "blockers": sync_output.get("blockers", []),
        }

        self._sync_summary = summary_payload

        # Send as agent.completed event with phase_data
        # The backend's _update_spec_phase_data() will merge this into the spec
        client = await self._get_client()
        endpoint = f"{self.callback_url}/api/v1/sandboxes/{self.sandbox_id}/events"

        event_payload = {
            "event_type": "agent.completed",
            "event_data": {
                "spec_id": spec_id,
                "success": sync_output.get("ready_for_execution", False),
                "phase_data": phase_data or {},
                "sync_summary": summary_payload,
            },
            "source": "agent",
        }

        for attempt in range(self.max_retries):
            try:
                response = await client.post(endpoint, json=event_payload)
                response.raise_for_status()
                return
            except httpx.HTTPError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)
                else:
                    print(f"Failed to send sync summary after {self.max_retries} attempts: {e}")

    @property
    def sync_summary(self) -> Optional[Dict[str, Any]]:
        """Get the last reported sync summary."""
        return self._sync_summary

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Flush and close on context exit."""
        await self.flush()
        await self.close()
