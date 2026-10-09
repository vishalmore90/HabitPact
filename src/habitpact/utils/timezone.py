"""Timezone validation helpers."""

from __future__ import annotations

from zoneinfo import ZoneInfo, available_timezones


def is_valid_timezone(tz_name: str) -> bool:
    """Check if a timezone string is a valid IANA timezone."""
    try:
        ZoneInfo(tz_name)
        return tz_name in available_timezones() or tz_name == "UTC"
    except (KeyError, ValueError):
        return False
