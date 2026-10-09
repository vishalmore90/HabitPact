"""Tests for the database models and engine lifecycle."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from habitpact.db.engine import close_db, get_session, init_db
from habitpact.db.models import Checkin, Guild, Habit, User


@pytest.fixture()
async def db_session() -> AsyncSession:
    """Initialize an in-memory database and return a session."""
    await init_db("sqlite+aiosqlite:///:memory:")
    async for session in get_session():
        yield session
    await close_db()


@pytest.fixture()
async def sample_guild(db_session: AsyncSession) -> Guild:
    """Create and return a sample guild."""
    guild = Guild(id=123456789, name="Test Server")
    db_session.add(guild)
    await db_session.commit()
    await db_session.refresh(guild)
    return guild


@pytest.fixture()
async def sample_user(db_session: AsyncSession, sample_guild: Guild) -> User:
    """Create and return a sample user in the sample guild."""
    user = User(discord_id=987654321, guild_id=sample_guild.id, timezone="Asia/Kolkata")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture()
async def sample_habit(db_session: AsyncSession, sample_user: User) -> Habit:
    """Create and return a sample habit."""
    habit = Habit(user_id=sample_user.id, name="Read 30 minutes")
    db_session.add(habit)
    await db_session.commit()
    await db_session.refresh(habit)
    return habit


class TestGuildModel:
    """Tests for the Guild model."""

    async def test_create_guild(self, db_session: AsyncSession) -> None:
        guild = Guild(id=111, name="My Server")
        db_session.add(guild)
        await db_session.commit()

        result = await db_session.get(Guild, 111)
        assert result is not None
        assert result.name == "My Server"
        assert result.joined_at is not None

    async def test_guild_repr(self, sample_guild: Guild) -> None:
        assert "Test Server" in repr(sample_guild)


class TestUserModel:
    """Tests for the User model."""

    async def test_create_user(self, db_session: AsyncSession, sample_guild: Guild) -> None:
        user = User(discord_id=111, guild_id=sample_guild.id)
        db_session.add(user)
        await db_session.commit()

        assert user.id is not None
        assert user.timezone == "UTC"
        assert user.remind_at is None

    async def test_unique_discord_guild(
        self, db_session: AsyncSession, sample_guild: Guild
    ) -> None:
        """A user cannot have two profiles in the same guild."""
        user1 = User(discord_id=111, guild_id=sample_guild.id)
        user2 = User(discord_id=111, guild_id=sample_guild.id)
        db_session.add(user1)
        await db_session.commit()

        db_session.add(user2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_user_different_guilds(self, db_session: AsyncSession) -> None:
        """Same Discord user can exist in different guilds."""
        guild_a = Guild(id=100, name="Server A")
        guild_b = Guild(id=200, name="Server B")
        db_session.add_all([guild_a, guild_b])
        await db_session.commit()

        user_a = User(discord_id=999, guild_id=guild_a.id)
        user_b = User(discord_id=999, guild_id=guild_b.id)
        db_session.add_all([user_a, user_b])
        await db_session.commit()

        assert user_a.id != user_b.id


class TestHabitModel:
    """Tests for the Habit model."""

    async def test_create_habit(self, db_session: AsyncSession, sample_user: User) -> None:
        habit = Habit(user_id=sample_user.id, name="Exercise")
        db_session.add(habit)
        await db_session.commit()

        assert habit.id is not None
        assert habit.is_active is True
        assert habit.archived_at is None

    async def test_unique_habit_name_per_user(
        self, db_session: AsyncSession, sample_user: User
    ) -> None:
        """A user cannot have two habits with the same name."""
        h1 = Habit(user_id=sample_user.id, name="Read")
        h2 = Habit(user_id=sample_user.id, name="Read")
        db_session.add(h1)
        await db_session.commit()

        db_session.add(h2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_soft_delete(self, db_session: AsyncSession, sample_habit: Habit) -> None:
        """Archiving a habit preserves it in the database."""
        sample_habit.archived_at = datetime.datetime.now(tz=datetime.UTC)
        await db_session.commit()
        await db_session.refresh(sample_habit)

        assert sample_habit.is_active is False
        assert sample_habit.archived_at is not None


class TestCheckinModel:
    """Tests for the Checkin model."""

    async def test_create_checkin(self, db_session: AsyncSession, sample_habit: Habit) -> None:
        checkin = Checkin(habit_id=sample_habit.id, checked_date=datetime.date(2026, 10, 9))
        db_session.add(checkin)
        await db_session.commit()

        assert checkin.id is not None
        assert checkin.checked_date == datetime.date(2026, 10, 9)

    async def test_one_checkin_per_day(
        self, db_session: AsyncSession, sample_habit: Habit
    ) -> None:
        """Cannot check in twice for the same habit on the same day."""
        today = datetime.date(2026, 10, 9)
        c1 = Checkin(habit_id=sample_habit.id, checked_date=today)
        c2 = Checkin(habit_id=sample_habit.id, checked_date=today)
        db_session.add(c1)
        await db_session.commit()

        db_session.add(c2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_different_days_ok(
        self, db_session: AsyncSession, sample_habit: Habit
    ) -> None:
        """Can check in on different days."""
        c1 = Checkin(habit_id=sample_habit.id, checked_date=datetime.date(2026, 10, 9))
        c2 = Checkin(habit_id=sample_habit.id, checked_date=datetime.date(2026, 10, 10))
        db_session.add_all([c1, c2])
        await db_session.commit()

        result = await db_session.execute(
            select(Checkin).where(Checkin.habit_id == sample_habit.id)
        )
        assert len(result.scalars().all()) == 2

    async def test_cascade_delete_guild(self, db_session: AsyncSession) -> None:
        """Deleting a guild cascades to users, habits, and checkins."""
        guild = Guild(id=777, name="Temp")
        db_session.add(guild)
        await db_session.commit()

        user = User(discord_id=888, guild_id=guild.id)
        db_session.add(user)
        await db_session.commit()

        habit = Habit(user_id=user.id, name="Test")
        db_session.add(habit)
        await db_session.commit()

        checkin = Checkin(habit_id=habit.id, checked_date=datetime.date(2026, 1, 1))
        db_session.add(checkin)
        await db_session.commit()

        # Delete the guild — everything should cascade
        await db_session.delete(guild)
        await db_session.commit()

        assert await db_session.get(User, user.id) is None
        assert await db_session.get(Habit, habit.id) is None
        assert await db_session.get(Checkin, checkin.id) is None
