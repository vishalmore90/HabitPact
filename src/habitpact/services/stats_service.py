"""Stats service — personal stats and guild leaderboard queries."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from habitpact.db.models import Habit, User
from habitpact.services.checkin_service import CheckinService, StreakInfo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HabitStat:
    """Streak info paired with its habit name."""

    habit_name: str
    streak: StreakInfo


@dataclass(frozen=True)
class LeaderboardEntry:
    """A single leaderboard row."""

    discord_id: int
    total_streak: int
    habit_count: int


class StatsService:
    """Handles personal stats and guild leaderboard computation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._checkin_svc = CheckinService(session)

    async def get_user_stats(self, user: User) -> list[HabitStat]:
        """
        Return streak stats for every active habit the user has.

        Results are sorted by current streak descending.
        """
        stmt = (
            select(Habit)
            .where(Habit.user_id == user.id, Habit.archived_at.is_(None))
            .order_by(Habit.created_at)
        )
        result = await self.session.execute(stmt)
        habits = list(result.scalars().all())

        stats: list[HabitStat] = []
        for habit in habits:
            streak = await self._checkin_svc.compute_streak(habit.id)
            stats.append(HabitStat(habit_name=habit.name, streak=streak))

        # Sort by current streak descending
        return sorted(stats, key=lambda s: s.streak.current_streak, reverse=True)

    async def get_guild_leaderboard(
        self, guild_id: int, limit: int = 10
    ) -> list[LeaderboardEntry]:
        """
        Return the top N users in a guild ranked by total active streak days.

        Total streak = sum of current_streak across all active habits.
        """
        # Fetch all users in the guild
        stmt = select(User).where(User.guild_id == guild_id)
        result = await self.session.execute(stmt)
        users = list(result.scalars().all())

        entries: list[LeaderboardEntry] = []
        for user in users:
            # Get active habits
            habit_stmt = select(Habit).where(
                Habit.user_id == user.id,
                Habit.archived_at.is_(None),
            )
            habit_result = await self.session.execute(habit_stmt)
            habits = list(habit_result.scalars().all())

            if not habits:
                continue

            total_streak = 0
            for habit in habits:
                streak = await self._checkin_svc.compute_streak(habit.id)
                total_streak += streak.current_streak

            if total_streak > 0:
                entries.append(
                    LeaderboardEntry(
                        discord_id=user.discord_id,
                        total_streak=total_streak,
                        habit_count=len(habits),
                    )
                )

        # Sort by total streak descending, take top N
        entries.sort(key=lambda e: e.total_streak, reverse=True)
        return entries[:limit]
