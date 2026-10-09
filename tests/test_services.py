"""Tests for the service layer."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from habitpact.db.engine import close_db, get_session, init_db
from habitpact.db.models import Checkin, Habit, User
from habitpact.services.checkin_service import CheckinService
from habitpact.services.guild_service import GuildService
from habitpact.services.habit_service import HabitService

# ── Fixtures ────────────────────────────────────────────────────────────────


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
async def checkin_svc(db_session: AsyncSession) -> CheckinService:
    return CheckinService(db_session)


@pytest.fixture()
async def sample_user(guild_svc: GuildService) -> User:
    return await guild_svc.get_or_create_user(
        discord_id=111, guild_id=100, guild_name="Test"
    )


# ── GuildService Tests ──────────────────────────────────────────────────────


class TestGuildService:
    async def test_get_or_create_guild_creates(self, guild_svc: GuildService) -> None:
        guild = await guild_svc.get_or_create_guild(100, "Test Server")
        assert guild.id == 100
        assert guild.name == "Test Server"

    async def test_get_or_create_guild_idempotent(self, guild_svc: GuildService) -> None:
        g1 = await guild_svc.get_or_create_guild(100, "Test")
        g2 = await guild_svc.get_or_create_guild(100, "Test")
        assert g1.id == g2.id

    async def test_get_or_create_user_creates(self, guild_svc: GuildService) -> None:
        user = await guild_svc.get_or_create_user(111, 100, "Test")
        assert user.discord_id == 111
        assert user.guild_id == 100
        assert user.timezone == "UTC"

    async def test_get_or_create_user_idempotent(self, guild_svc: GuildService) -> None:
        u1 = await guild_svc.get_or_create_user(111, 100, "Test")
        u2 = await guild_svc.get_or_create_user(111, 100, "Test")
        assert u1.id == u2.id

    async def test_update_timezone(
        self, guild_svc: GuildService, sample_user: User
    ) -> None:
        await guild_svc.update_timezone(sample_user, "Asia/Kolkata")
        assert sample_user.timezone == "Asia/Kolkata"

    async def test_update_reminder(
        self, guild_svc: GuildService, sample_user: User
    ) -> None:
        t = datetime.time(9, 0)
        await guild_svc.update_reminder(sample_user, t)
        assert sample_user.remind_at == t

        await guild_svc.update_reminder(sample_user, None)
        assert sample_user.remind_at is None


# ── HabitService Tests ───────────────────────────────────────────────────────


class TestHabitService:
    async def test_create_habit_success(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        result = await habit_svc.create_habit(sample_user, "Read 30 minutes")
        assert isinstance(result, Habit)
        assert result.name == "Read 30 minutes"
        assert result.is_active is True

    async def test_create_habit_empty_name(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        result = await habit_svc.create_habit(sample_user, "   ")
        assert isinstance(result, str)
        assert "empty" in result.lower()

    async def test_create_habit_too_long(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        result = await habit_svc.create_habit(sample_user, "x" * 101)
        assert isinstance(result, str)
        assert "100 characters" in result

    async def test_create_habit_duplicate(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        await habit_svc.create_habit(sample_user, "Read")
        result = await habit_svc.create_habit(sample_user, "Read")
        assert isinstance(result, str)
        assert "already" in result.lower()

    async def test_create_habit_duplicate_case_insensitive(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        await habit_svc.create_habit(sample_user, "Read")
        result = await habit_svc.create_habit(sample_user, "read")
        assert isinstance(result, str)

    async def test_max_habits_limit(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        for i in range(5):
            result = await habit_svc.create_habit(sample_user, f"Habit {i}")
            assert isinstance(result, Habit)

        result = await habit_svc.create_habit(sample_user, "Habit 5")
        assert isinstance(result, str)
        assert "up to 5" in result

    async def test_list_active_habits(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        await habit_svc.create_habit(sample_user, "A")
        await habit_svc.create_habit(sample_user, "B")
        habits = await habit_svc.list_active_habits(sample_user)
        assert len(habits) == 2
        assert habits[0].name == "A"

    async def test_delete_habit(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        await habit_svc.create_habit(sample_user, "Read")
        result = await habit_svc.delete_habit(sample_user, "Read")
        assert isinstance(result, Habit)
        assert result.is_active is False

        habits = await habit_svc.list_active_habits(sample_user)
        assert len(habits) == 0

    async def test_delete_nonexistent(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        result = await habit_svc.delete_habit(sample_user, "Nope")
        assert isinstance(result, str)
        assert "No active habit" in result

    async def test_delete_frees_slot(
        self, habit_svc: HabitService, sample_user: User
    ) -> None:
        """Deleting a habit frees up a slot for a new one."""
        for i in range(5):
            await habit_svc.create_habit(sample_user, f"H{i}")

        await habit_svc.delete_habit(sample_user, "H0")
        result = await habit_svc.create_habit(sample_user, "New Habit")
        assert isinstance(result, Habit)


# ── CheckinService Tests ────────────────────────────────────────────────────


class TestCheckinService:
    async def _create_habit(
        self, habit_svc: HabitService, user: User, name: str = "Read"
    ) -> Habit:
        result = await habit_svc.create_habit(user, name)
        assert isinstance(result, Habit)
        return result

    async def _insert_checkins(
        self,
        db_session: AsyncSession,
        habit_id: int,
        dates: list[datetime.date],
    ) -> None:
        for d in dates:
            db_session.add(Checkin(habit_id=habit_id, checked_date=d))
        await db_session.commit()

    async def test_checkin_success(
        self,
        checkin_svc: CheckinService,
        habit_svc: HabitService,
        sample_user: User,
    ) -> None:
        habit = await self._create_habit(habit_svc, sample_user)
        result = await checkin_svc.perform_checkin(habit, "UTC")
        assert result.success is True
        assert result.streak is not None
        assert result.streak.current_streak == 1

    async def test_checkin_duplicate(
        self,
        checkin_svc: CheckinService,
        habit_svc: HabitService,
        sample_user: User,
    ) -> None:
        habit = await self._create_habit(habit_svc, sample_user)
        await checkin_svc.perform_checkin(habit, "UTC")
        result = await checkin_svc.perform_checkin(habit, "UTC")
        assert result.success is False
        assert "already" in result.message.lower()

    async def test_streak_consecutive_days(
        self,
        checkin_svc: CheckinService,
        habit_svc: HabitService,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        habit = await self._create_habit(habit_svc, sample_user)
        today = datetime.date(2026, 10, 9)
        dates = [today - datetime.timedelta(days=i) for i in range(5)]
        await self._insert_checkins(db_session, habit.id, dates)

        streak = await checkin_svc.compute_streak(habit.id, today)
        assert streak.current_streak == 5
        assert streak.longest_streak == 5
        assert streak.total_checkins == 5

    async def test_streak_with_gap(
        self,
        checkin_svc: CheckinService,
        habit_svc: HabitService,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        habit = await self._create_habit(habit_svc, sample_user)
        today = datetime.date(2026, 10, 9)
        # 3-day current streak, then a gap, then 2-day old streak
        dates = [
            today,
            today - datetime.timedelta(days=1),
            today - datetime.timedelta(days=2),
            # gap at day 3
            today - datetime.timedelta(days=4),
            today - datetime.timedelta(days=5),
        ]
        await self._insert_checkins(db_session, habit.id, dates)

        streak = await checkin_svc.compute_streak(habit.id, today)
        assert streak.current_streak == 3
        assert streak.longest_streak == 3  # both segments are ≤ 3
        assert streak.total_checkins == 5

    async def test_streak_no_checkins(
        self,
        checkin_svc: CheckinService,
        habit_svc: HabitService,
        sample_user: User,
    ) -> None:
        habit = await self._create_habit(habit_svc, sample_user)
        streak = await checkin_svc.compute_streak(habit.id)
        assert streak.current_streak == 0
        assert streak.longest_streak == 0
        assert streak.total_checkins == 0

    async def test_milestone_detection(
        self,
        checkin_svc: CheckinService,
        habit_svc: HabitService,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        habit = await self._create_habit(habit_svc, sample_user)
        today = datetime.date(2026, 10, 9)
        # 7 consecutive days → milestone
        dates = [today - datetime.timedelta(days=i) for i in range(7)]
        await self._insert_checkins(db_session, habit.id, dates)

        streak = await checkin_svc.compute_streak(habit.id, today)
        assert streak.current_streak == 7
        assert streak.is_milestone is True

    async def test_no_milestone_at_6(
        self,
        checkin_svc: CheckinService,
        habit_svc: HabitService,
        sample_user: User,
        db_session: AsyncSession,
    ) -> None:
        habit = await self._create_habit(habit_svc, sample_user)
        today = datetime.date(2026, 10, 9)
        dates = [today - datetime.timedelta(days=i) for i in range(6)]
        await self._insert_checkins(db_session, habit.id, dates)

        streak = await checkin_svc.compute_streak(habit.id, today)
        assert streak.current_streak == 6
        assert streak.is_milestone is False
