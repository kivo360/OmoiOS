"""Base reporter abstraction.

All reporters implement this interface. Events have the same format
regardless of destination (array, file, HTTP).
"""

from abc import ABC, abstractmethod
from typing import List

from spec_sandbox.schemas.events import Event


class Reporter(ABC):
    """Abstract reporter - where events go.

    Implementations:
    - ArrayReporter: In-memory list (for tests)
    - JSONLReporter: Append-only file (for local debugging)
    - HTTPReporter: POST to callback URL (for production)
    """

    @abstractmethod
    async def report(self, event: Event) -> None:
        """Report a single event."""
        pass

    @abstractmethod
    async def flush(self) -> None:
        """Ensure all events are persisted."""
        pass

    async def report_many(self, events: List[Event]) -> None:
        """Report multiple events (default: sequential)."""
        for event in events:
            await self.report(event)
        await self.flush()

    async def __aenter__(self) -> "Reporter":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - flush on exit."""
        await self.flush()
