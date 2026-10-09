"""Tests for StatsService."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from habitpact.db.engine import close_db, get_session, init_db
from habitpact.db.models import Checkin, Habit
from habitpact.services.guild_service import GuildService
from habitpact.services.habit_service import HabitService
from habitpact.services.stats_service import StatsService


@pytest.fixture()
async def db_session() -> AsyncSession:
    await init_db("sqlite+aiosqlite:///:memory:")
    async for session in get_session():
        yield session
    await close_db()


@pytest.fixture()
async def guild_svc(db_session: AsyncSession) -> GuildService:
    return GuildService(db_session)


@pytest.fixture()
async def habit_svc(db_session: AsyncSession) -> HabitService:
    return HabitService(db_session)


@pytest.fixture()
async def stats_svc(db_session: AsyncSession) -> StatsService:
    return StatsService(db_session)


async def _seed_checkins(
    db_session: AsyncSession, habit_id: int, dates: list[datetime.date]
) -> None:
    for d in dates:
        db_session.add(Checkin(habit_id=habit_id, checked_date=d))
    await db_session.commit()


class TestStatsService:
    async def test_no_habits_returns_empty(
        self,
        stats_svc: StatsService,
        guild_svc: GuildService,
    ) -> None:
        user = await guild_svc.get_or_create_user(1, 100, "Test")
        result = await stats_svc.get_user_stats(user)
        assert result == []

    async def test_user_stats_single_habit(
        self,
        stats_svc: StatsService,
        guild_svc: GuildService,
        habit_svc: HabitService,
        db_session: AsyncSession,
    ) -> None:
        user = await guild_svc.get_or_create_user(1, 100, "Test")
        h = await habit_svc.create_habit(user, "Read")
        assert isinstance(h, Habit)

        today = datetime.date(2026, 10, 9)
        dates = [today - datetime.timedelta(days=i) for i in range(3)]
        await _seed_checkins(db_session, h.id, dates)

        result = await stats_svc.get_user_stats(user)
        assert len(result) == 1
        assert result[0].habit_name == "Read"
        assert result[0].streak.current_streak == 3
        assert result[0].streak.total_checkins == 3

    async def test_user_stats_sorted_by_streak(
        self,
        stats_svc: StatsService,
        guild_svc: GuildService,
        habit_svc: HabitService,
        db_session: AsyncSession,
    ) -> None:
        """Habits are sorted descending by current streak."""
        user = await guild_svc.get_or_create_user(1, 100, "Test")
        h1 = await habit_svc.create_habit(user, "Habit A")
        h2 = await habit_svc.create_habit(user, "Habit B")
        assert isinstance(h1, Habit)
        assert isinstance(h2, Habit)

        today = datetime.date(2026, 10, 9)
        # h1 has 2-day streak, h2 has 5-day streak
        await _seed_checkins(db_session, h1.id, [today, today - datetime.timedelta(days=1)])
        await _seed_checkins(
            db_session, h2.id, [today - datetime.timedelta(days=i) for i in range(5)]
        )

        result = await stats_svc.get_user_stats(user)
        assert result[0].habit_name == "Habit B"  # highest streak first
        assert result[1].habit_name == "Habit A"

    async def test_leaderboard_empty(
        self,
        stats_svc: StatsService,
        guild_svc: GuildService,
    ) -> None:
        """Guild with no check-ins returns empty leaderboard."""
        await guild_svc.get_or_create_user(1, 200, "Empty Guild")
        result = await stats_svc.get_guild_leaderboard(200)
        assert result == []

    async def test_leaderboard_ranking(
        self,
        stats_svc: StatsService,
        guild_svc: GuildService,
        habit_svc: HabitService,
        db_session: AsyncSession,
    ) -> None:
        """Users are ranked by total active streak days, descending."""
        user_a = await guild_svc.get_or_create_user(1, 300, "Guild")
        user_b = await guild_svc.get_or_create_user(2, 300, "Guild")

        h_a = await habit_svc.create_habit(user_a, "Habit A")
        h_b = await habit_svc.create_habit(user_b, "Habit B")
        assert isinstance(h_a, Habit)
        assert isinstance(h_b, Habit)

        today = datetime.date(2026, 10, 9)
        # User A: 2-day streak, User B: 7-day streak
        await _seed_checkins(db_session, h_a.id, [today, today - datetime.timedelta(days=1)])
        await _seed_checkins(
            db_session, h_b.id, [today - datetime.timedelta(days=i) for i in range(7)]
        )

        result = await stats_svc.get_guild_leaderboard(300)
        assert len(result) == 2
        assert result[0].discord_id == 2   # user_b has more streak
        assert result[0].total_streak == 7
        assert result[1].discord_id == 1
        assert result[1].total_streak == 2

    async def test_leaderboard_limit(
        self,
        stats_svc: StatsService,
        guild_svc: GuildService,
        habit_svc: HabitService,
        db_session: AsyncSession,
    ) -> None:
        """Leaderboard respects the limit parameter."""
        today = datetime.date(2026, 10, 9)
        for i in range(1, 6):  # 5 users
            user = await guild_svc.get_or_create_user(i, 400, "Big Guild")
            h = await habit_svc.create_habit(user, "Run")
            assert isinstance(h, Habit)
            await _seed_checkins(
                db_session, h.id, [today - datetime.timedelta(days=j) for j in range(i)]
            )

        result = await stats_svc.get_guild_leaderboard(400, limit=3)
        assert len(result) == 3
