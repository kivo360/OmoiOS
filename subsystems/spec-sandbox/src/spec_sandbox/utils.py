"""Utility functions for spec sandbox."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)
