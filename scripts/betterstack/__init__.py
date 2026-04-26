"""BetterStack toolkit — manage Telemetry, Errors, and Uptime from one place.

Public surface:
    BetterStack — REST client wrapping all three product APIs
    ResourceNotFound, BetterStackAPIError — error types
"""

from .api import BetterStack, BetterStackAPIError, ResourceNotFound

__all__ = ["BetterStack", "BetterStackAPIError", "ResourceNotFound"]
