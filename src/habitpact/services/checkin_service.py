"""Service for check-ins and streak calculation."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from habitpact.db.models import Checkin, Habit

logger = logging.getLogger(__name__)

MILESTONES = {7, 14, 30, 60, 100, 200, 365}


@dataclass(frozen=True)
class StreakInfo:
    """Computed streak data for a single habit."""

    current_streak: int
    longest_streak: int
    total_checkins: int
    is_milestone: bool


@dataclass(frozen=True)
class CheckinResult:
    """Result of a check-in attempt."""

    success: bool
    message: str
    streak: StreakInfo | None = None


class CheckinService:
    """Handles daily check-ins and streak computation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def perform_checkin(
        self,
        habit: Habit,
        user_timezone: str,
    ) -> CheckinResult:
        """
        Record a check-in for today (in the user's timezone).

        Returns a CheckinResult with success status, message, and streak info.
        """
        today = self._today_in_tz(user_timezone)

        # Check for duplicate
        existing = await self._get_checkin(habit.id, today)
        if existing is not None:
            return CheckinResult(
                success=False,
                message=f"You already checked in for **{habit.name}** today! 🎉",
            )

        # Record the check-in
        checkin = Checkin(habit_id=habit.id, checked_date=today)
        self.session.add(checkin)
        await self.session.commit()

        # Compute streak
        streak = await self.compute_streak(habit.id, today)

        # Build message
        streak_days = streak.current_streak
        msg = f"✅ Checked in for **{habit.name}**! Current streak: **{streak_days} day(s)**."
        if streak.is_milestone:
            msg += f"\n🏆 **Milestone reached: {streak.current_streak} days!** Keep it up!"

        return CheckinResult(success=True, message=msg, streak=streak)

    async def compute_streak(
        self,
        habit_id: int,
        reference_date: datetime.date | None = None,
    ) -> StreakInfo:
        """
        Compute current streak, longest streak, and total check-ins for a habit.

        The streak is computed by walking backwards from reference_date.
        """
        dates = await self._get_all_checkin_dates(habit_id)

        if not dates:
            return StreakInfo(
                current_streak=0, longest_streak=0, total_checkins=0, is_milestone=False
            )

        if reference_date is None:
            reference_date = dates[0]  # most recent

        date_set = set(dates)
        total = len(dates)

        # Current streak: walk backwards from reference_date
        current = 0
        day = reference_date
        while day in date_set:
            current += 1
            day -= datetime.timedelta(days=1)

        # Longest streak: scan all dates
        longest = 0
        streak = 0
        prev: datetime.date | None = None
        for d in sorted(dates):
            if prev is not None and (d - prev).days == 1:
                streak += 1
            else:
                streak = 1
            longest = max(longest, streak)
            prev = d

        is_milestone = current in MILESTONES

        return StreakInfo(
            current_streak=current,
            longest_streak=longest,
            total_checkins=total,
            is_milestone=is_milestone,
        )

    async def _get_checkin(self, habit_id: int, date: datetime.date) -> Checkin | None:
        """Get a specific check-in by habit and date."""
        stmt = select(Checkin).where(
            Checkin.habit_id == habit_id,
            Checkin.checked_date == date,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_all_checkin_dates(self, habit_id: int) -> list[datetime.date]:
        """Get all check-in dates for a habit, sorted descending."""
        stmt = (
            select(Checkin.checked_date)
            .where(Checkin.habit_id == habit_id)
            .order_by(Checkin.checked_date.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _today_in_tz(timezone: str) -> datetime.date:
        """Get today's date in the given timezone."""
        try:
            tz = ZoneInfo(timezone)
        except (KeyError, ValueError):
            tz = ZoneInfo("UTC")
        return datetime.datetime.now(tz=tz).date()
