"""HTTP reporter for production (Daytona sandboxes).

POSTs events to callback URL with batching and retry logic.
"""

import asyncio
from typing import List, Optional

import httpx

from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event


class HTTPReporter(Reporter):
    """POSTs events to callback URL (production mode).

    Features:
    - Batching: Collects events and sends in batches
    - Retry: Retries failed requests with exponential backoff
    - Timeout: Configurable request timeout

    Usage:
        reporter = HTTPReporter(
            callback_url="https://api.omoios.dev",
            batch_size=10,
        )
        machine = SpecStateMachine(reporter=reporter, ...)
        await machine.run()
    """

    def __init__(
        self,
        callback_url: str,
        batch_size: int = 10,
        flush_interval: float = 5.0,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self.callback_url = callback_url.rstrip("/")
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.timeout = timeout
        self.max_retries = max_retries

        self._buffer: List[Event] = []
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def report(self, event: Event) -> None:
        """Add event to buffer, flush if batch size reached."""
        self._buffer.append(event)

        if len(self._buffer) >= self.batch_size:
            await self.flush()

    async def flush(self) -> None:
        """Send buffered events to callback URL."""
        if not self._buffer:
            return

        events_to_send = self._buffer.copy()
        self._buffer.clear()

        client = await self._get_client()

        for attempt in range(self.max_retries):
            try:
                response = await client.post(
                    f"{self.callback_url}/api/v1/sandbox/events",
                    json=[e.model_dump(mode="json") for e in events_to_send],
                )
                response.raise_for_status()
                return
            except httpx.HTTPError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff
                else:
                    # On final failure, log but don't crash
                    # Events are lost but execution continues
                    print(
                        f"Failed to send events after {self.max_retries} attempts: {e}"
                    )

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Flush and close on context exit."""
        await self.flush()
        await self.close()
