"""
Timezone-aware datetime utilities.

This module provides helpers for working with UTC timestamps in a way that's
compatible with Python 3.12+ and SQLAlchemy's timezone-aware datetime columns.

DEPRECATION NOTE:
- datetime.utcnow() is deprecated in Python 3.12+
- It returns naive datetime objects (no timezone info)
- This can cause issues with timezone-aware comparisons

REPLACEMENT:
- Use datetime.now(timezone.utc) instead
- Returns timezone-aware datetime objects
- Compatible with SQLAlchemy DateTime(timezone=True) columns
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """
    Get current UTC time as a timezone-aware datetime object.

    This is the recommended replacement for datetime.utcnow() which is
    deprecated in Python 3.12+.

    Returns:
        datetime: Current UTC time with timezone info (timezone.utc)

    Example:
        >>> from app.utils.datetime import utcnow
        >>> now = utcnow()
        >>> print(now)  # 2025-10-31 12:34:56+00:00
        >>> print(now.tzinfo)  # UTC
    """
    return datetime.now(timezone.utc)


def utcnow_naive() -> datetime:
    """
    Get current UTC time as a timezone-naive datetime object.

    Use this for SQLAlchemy column defaults when the database column
    is TIMESTAMP WITHOUT TIME ZONE (which is the default in PostgreSQL).

    Returns:
        datetime: Current UTC time without timezone info (naive)

    Example:
        >>> from app.utils.datetime import utcnow_naive
        >>> now = utcnow_naive()
        >>> print(now)  # 2025-10-31 12:34:56
        >>> print(now.tzinfo)  # None
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def timestamp_to_datetime(timestamp: int) -> datetime:
    """
    Convert Unix timestamp to timezone-aware UTC datetime.

    Args:
        timestamp: Unix timestamp (seconds since epoch)

    Returns:
        datetime: Timezone-aware datetime in UTC

    Example:
        >>> ts = 1698763200
        >>> dt = timestamp_to_datetime(ts)
        >>> print(dt)  # 2023-10-31 12:00:00+00:00
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert datetime to Unix timestamp.

    Args:
        dt: Datetime object (timezone-aware or naive, interpreted as UTC if naive)

    Returns:
        int: Unix timestamp (seconds since epoch)

    Example:
        >>> from app.utils.datetime import utcnow, datetime_to_timestamp
        >>> now = utcnow()
        >>> ts = datetime_to_timestamp(now)
        >>> print(ts)  # 1698763200
    """
    return int(dt.timestamp())
