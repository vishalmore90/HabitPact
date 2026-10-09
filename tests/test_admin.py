"""Tests for the admin cog helpers and timezone utilities."""

from __future__ import annotations

import datetime

from habitpact.cogs.admin import _parse_time
from habitpact.utils.timezone import is_valid_timezone


class TestParseTime:
    """Tests for the _parse_time helper."""

    def test_valid_time(self) -> None:
        result = _parse_time("09:00")
        assert result == datetime.time(9, 0)

    def test_valid_time_evening(self) -> None:
        result = _parse_time("20:30")
        assert result == datetime.time(20, 30)

    def test_midnight(self) -> None:
        result = _parse_time("00:00")
        assert result == datetime.time(0, 0)

    def test_invalid_format_no_colon(self) -> None:
        assert _parse_time("0900") is None

    def test_invalid_hour(self) -> None:
        assert _parse_time("25:00") is None

    def test_invalid_minute(self) -> None:
        assert _parse_time("09:60") is None

    def test_empty_string(self) -> None:
        assert _parse_time("") is None

    def test_non_numeric(self) -> None:
        assert _parse_time("ab:cd") is None

    def test_extra_colons(self) -> None:
        assert _parse_time("09:00:00") is None


class TestTimezoneValidation:
    """Tests for the is_valid_timezone helper."""

    def test_utc_valid(self) -> None:
        assert is_valid_timezone("UTC") is True

    def test_kolkata_valid(self) -> None:
        assert is_valid_timezone("Asia/Kolkata") is True

    def test_eastern_valid(self) -> None:
        assert is_valid_timezone("US/Eastern") is True

    def test_london_valid(self) -> None:
        assert is_valid_timezone("Europe/London") is True

    def test_invalid_timezone(self) -> None:
        assert is_valid_timezone("Not/ATimezone") is False

    def test_empty_string(self) -> None:
        assert is_valid_timezone("") is False

    def test_random_string(self) -> None:
        assert is_valid_timezone("banana") is False
