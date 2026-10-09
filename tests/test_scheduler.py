"""Tests for scheduler time-matching and reminder logic."""

from __future__ import annotations

import datetime

# We test the time-matching logic that lives in the scheduler
# by extracting it into a pure function we can verify independently.

def _should_remind(
    remind_at: datetime.time,
    now_local: datetime.datetime,
) -> bool:
    """Mirror of the matching logic used in HabitScheduler._send_reminders."""
    return (
        now_local.hour == remind_at.hour
        and now_local.minute == remind_at.minute
    )


class TestReminderTimeMatching:
    """Test the timezone-aware time-matching logic used by the scheduler."""

    def _make_dt(self, hour: int, minute: int) -> datetime.datetime:
        return datetime.datetime(2026, 10, 9, hour, minute, tzinfo=datetime.timezone.utc)

    def test_exact_match(self) -> None:
        remind = datetime.time(9, 0)
        now = self._make_dt(9, 0)
        assert _should_remind(remind, now) is True

    def test_no_match_different_hour(self) -> None:
        remind = datetime.time(9, 0)
        now = self._make_dt(10, 0)
        assert _should_remind(remind, now) is False

    def test_no_match_different_minute(self) -> None:
        remind = datetime.time(9, 0)
        now = self._make_dt(9, 1)
        assert _should_remind(remind, now) is False

    def test_midnight_match(self) -> None:
        remind = datetime.time(0, 0)
        now = self._make_dt(0, 0)
        assert _should_remind(remind, now) is True

    def test_late_night_match(self) -> None:
        remind = datetime.time(23, 59)
        now = self._make_dt(23, 59)
        assert _should_remind(remind, now) is True

    def test_seconds_ignored(self) -> None:
        """Reminder fires regardless of seconds within the matching minute."""
        remind = datetime.time(9, 0)
        now = datetime.datetime(2026, 10, 9, 9, 0, 45, tzinfo=datetime.timezone.utc)
        assert _should_remind(remind, now) is True

    def test_no_match_one_minute_early(self) -> None:
        remind = datetime.time(9, 30)
        now = self._make_dt(9, 29)
        assert _should_remind(remind, now) is False

    def test_no_match_one_minute_late(self) -> None:
        remind = datetime.time(9, 30)
        now = self._make_dt(9, 31)
        assert _should_remind(remind, now) is False
