"""Datetime utilities for consistent timezone handling across the application."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime.

    This is the recommended way to get current time for all timestamps
    in the application. It ensures:
    - All timestamps are timezone-aware (not naive)
    - All timestamps use UTC (not local time)
    - Compatible with Python 3.12+ (datetime.utcnow() is deprecated)

    Returns:
        Current UTC time as timezone-aware datetime

    Example:
        >>> from sbir_cet_classifier.common.datetime_utils import utc_now
        >>> timestamp = utc_now()
        >>> print(timestamp.tzinfo)
        UTC
    """
    return datetime.now(timezone.utc)
