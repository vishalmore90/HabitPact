"""Service for guild and user management."""

from __future__ import annotations

import datetime
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from habitpact.db.models import Guild, User

logger = logging.getLogger(__name__)


class GuildService:
    """Handles guild registration and user profile management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_guild(self, guild_id: int, guild_name: str) -> Guild:
        """Ensure a guild record exists, creating it if necessary."""
        guild = await self.session.get(Guild, guild_id)
        if guild is None:
            guild = Guild(id=guild_id, name=guild_name)
            self.session.add(guild)
            await self.session.commit()
            await self.session.refresh(guild)
            logger.info("Registered new guild: %s (%d)", guild_name, guild_id)
        return guild

    async def get_or_create_user(
        self,
        discord_id: int,
        guild_id: int,
        guild_name: str,
    ) -> User:
        """
        Ensure a user profile exists for the given Discord user in the given guild.

        Creates the guild if it doesn't exist either.
        """
        await self.get_or_create_guild(guild_id, guild_name)

        stmt = select(User).where(
            User.discord_id == discord_id,
            User.guild_id == guild_id,
        )
        result = await self.session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            user = User(discord_id=discord_id, guild_id=guild_id)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            logger.info("Created user profile: discord=%d guild=%d", discord_id, guild_id)

        return user

    async def update_timezone(self, user: User, timezone: str) -> None:
        """Update a user's timezone setting."""
        user.timezone = timezone
        await self.session.commit()

    async def update_reminder(self, user: User, remind_at: datetime.time | None) -> None:
        """Update a user's daily reminder time. Pass None to disable."""
        user.remind_at = remind_at
        await self.session.commit()
