"""Datetime and serialization utilities."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from whenever import Instant


def utc_now() -> datetime:
    """
    Get current UTC datetime as a timezone-aware datetime object.

    Uses whenever library internally for proper UTC handling, but returns
    a standard datetime object for SQLAlchemy compatibility.

    Returns:
        datetime: Current UTC time as timezone-aware datetime
    """
    return Instant.now().py_datetime()


def utc_datetime(year: int, month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0, microsecond: int = 0) -> datetime:
    """
    Create a UTC datetime from components.

    Args:
        year: Year
        month: Month (1-12)
        day: Day (1-31)
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)
        microsecond: Microsecond (0-999999)

    Returns:
        datetime: UTC datetime as timezone-aware datetime
    """
    instant = Instant.from_utc(year, month, day, hour, minute, second, microsecond)
    return instant.py_datetime()


def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively convert non-JSON-serializable objects to serializable types.

    Handles:
    - UUID -> str
    - Enum -> value
    - datetime -> ISO format string
    - dict -> recursively sanitized dict
    - list/tuple -> recursively sanitized list

    Args:
        obj: Object to sanitize

    Returns:
        JSON-serializable version of the object
    """
    if obj is None:
        return None
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    if hasattr(obj, '__dict__'):
        # Handle objects with __dict__ (convert to dict)
        return sanitize_for_json(obj.__dict__)
    # Return as-is for basic types (str, int, float, bool)
    return obj

