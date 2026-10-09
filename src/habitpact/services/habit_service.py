"""Service for habit CRUD operations."""

from __future__ import annotations

import datetime
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from habitpact.db.models import Habit, User

logger = logging.getLogger(__name__)

MAX_ACTIVE_HABITS = 5


class HabitService:
    """Handles habit creation, listing, and deletion (soft-delete)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_habit(self, user: User, name: str) -> Habit | str:
        """
        Create a new habit for the user.

        Returns the Habit on success, or an error message string on failure.
        """
        name = name.strip()
        if not name:
            return "Habit name cannot be empty."

        if len(name) > 100:
            return "Habit name must be 100 characters or fewer."

        # Check active habit count
        count = await self._active_habit_count(user.id)
        if count >= MAX_ACTIVE_HABITS:
            return f"You can have up to {MAX_ACTIVE_HABITS} active habits. Delete one first."

        # Check for duplicate name (among active habits)
        existing = await self._find_active_habit(user.id, name)
        if existing is not None:
            return f"You already have a habit called **{name}**."

        habit = Habit(user_id=user.id, name=name)
        self.session.add(habit)
        await self.session.commit()
        await self.session.refresh(habit)
        logger.info("Created habit '%s' for user %d", name, user.id)
        return habit

    async def list_active_habits(self, user: User) -> list[Habit]:
        """Return all active (non-archived) habits for the user."""
        stmt = (
            select(Habit)
            .where(Habit.user_id == user.id, Habit.archived_at.is_(None))
            .order_by(Habit.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_habit(self, user: User, name: str) -> Habit | str:
        """
        Soft-delete a habit by name.

        Returns the archived Habit on success, or an error message string.
        """
        habit = await self._find_active_habit(user.id, name.strip())
        if habit is None:
            return f"No active habit found called **{name}**."

        habit.archived_at = datetime.datetime.now(tz=datetime.timezone.utc)
        await self.session.commit()
        logger.info("Archived habit '%s' for user %d", name, user.id)
        return habit

    async def _active_habit_count(self, user_id: int) -> int:
        """Count the number of active habits for a user."""
        stmt = select(func.count()).where(
            Habit.user_id == user_id,
            Habit.archived_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def _find_active_habit(self, user_id: int, name: str) -> Habit | None:
        """Find an active habit by name (case-insensitive)."""
        stmt = select(Habit).where(
            Habit.user_id == user_id,
            func.lower(Habit.name) == name.lower(),
            Habit.archived_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
