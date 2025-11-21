"""Datetime utilities using whenever library for timezone-aware datetime handling."""

from datetime import datetime

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

