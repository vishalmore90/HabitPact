"""APScheduler background tasks: daily reminders and weekly guild reports."""

from __future__ import annotations

import datetime
import logging
from zoneinfo import ZoneInfo

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore[import-untyped]
from apscheduler.triggers.cron import CronTrigger  # type: ignore[import-untyped]
from sqlalchemy import select

from habitpact.db.engine import get_session
from habitpact.db.models import Habit, User
from habitpact.services.stats_service import StatsService
from habitpact.utils.embeds import COLOR_STREAK

logger = logging.getLogger(__name__)


class HabitScheduler:
    """
    Manages all scheduled background tasks for the bot.

    Tasks:
      - Daily reminder: checks every minute for users whose remind_at matches
        the current time in their timezone; sends a DM.
      - Weekly report: every Monday at 09:00 UTC; posts a guild summary.
    """

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._scheduler = AsyncIOScheduler()

    def start(self) -> None:
        """Register jobs and start the scheduler."""
        # Check reminders every minute
        self._scheduler.add_job(
            self._send_reminders,
            trigger=CronTrigger(minute="*"),
            id="daily_reminders",
            replace_existing=True,
        )

        # Weekly guild report every Monday at 09:00 UTC
        self._scheduler.add_job(
            self._send_weekly_reports,
            trigger=CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="UTC"),
            id="weekly_reports",
            replace_existing=True,
        )

        self._scheduler.start()
        logger.info("Scheduler started. Jobs: daily_reminders, weekly_reports.")

    def stop(self) -> None:
        """Gracefully shut down the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped.")

    async def _send_reminders(self) -> None:
        """
        Every minute: find all users whose remind_at matches the current
        minute in their timezone, and send them a DM.
        """
        now_utc = datetime.datetime.now(tz=datetime.timezone.utc)

        async for session in get_session():
            stmt = select(User).where(User.remind_at.is_not(None))
            result = await session.execute(stmt)
            users = list(result.scalars().all())

        for user in users:
            if user.remind_at is None:
                continue

            try:
                tz = ZoneInfo(user.timezone)
            except (KeyError, ValueError):
                tz = ZoneInfo("UTC")

            now_local = now_utc.astimezone(tz)

            # Match HH:MM only
            if (
                now_local.hour == user.remind_at.hour
                and now_local.minute == user.remind_at.minute
            ):
                await self._dm_reminder(user)

    async def _dm_reminder(self, user: User) -> None:
        """Send a daily habit reminder DM to a user."""
        discord_user = self.bot.get_user(user.discord_id)
        if discord_user is None:
            try:
                discord_user = await self.bot.fetch_user(user.discord_id)
            except discord.NotFound:
                logger.warning(
                    "Could not find Discord user %d for reminder.", user.discord_id
                )
                return

        embed = discord.Embed(
            title="🔔 Daily Habit Reminder",
            description=(
                "Time to check in on your habits!\n\n"
                "Use `/checkin <habit>` to log your progress and keep your streak alive. 🔥"
            ),
            colour=COLOR_STREAK,
        )
        embed.set_footer(
            text=f"To disable reminders, use /remind off | Timezone: {user.timezone}"
        )

        try:
            await discord_user.send(embed=embed)
            logger.info("Sent reminder DM to user %d.", user.discord_id)
        except discord.Forbidden:
            logger.warning(
                "Cannot DM user %d (DMs disabled).", user.discord_id
            )

    async def _send_weekly_reports(self) -> None:
        """
        Every Monday at 09:00 UTC: post a weekly summary to each guild
        that has at least one user with active habits.
        """
        for guild in self.bot.guilds:
            await self._post_guild_report(guild)

    async def _post_guild_report(self, guild: discord.Guild) -> None:
        """Post a weekly habit summary embed to the first available text channel."""
        async for session in get_session():
            stats_svc = StatsService(session)
            entries = await stats_svc.get_guild_leaderboard(guild.id, limit=5)

            if not entries:
                return  # No active habits in this guild

            # Count total active habits in the guild
            stmt = (
                select(Habit)
                .join(User, Habit.user_id == User.id)
                .where(User.guild_id == guild.id, Habit.archived_at.is_(None))
            )
            result = await session.execute(stmt)
            habit_count = len(result.scalars().all())

        embed = discord.Embed(
            title=f"📅 Weekly Habit Report — {guild.name}",
            description=(
                f"Here's how the community did this week!\n"
                f"**{habit_count}** active habit(s) being tracked."
            ),
            colour=discord.Colour.gold(),
        )

        lines = []
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for rank, entry in enumerate(entries, start=1):
            medal = medals.get(rank, f"#{rank}")
            member = guild.get_member(entry.discord_id)
            name = member.display_name if member else f"User {entry.discord_id}"
            lines.append(
                f"{medal} **{name}** — {entry.total_streak} streak day(s)"
            )

        embed.add_field(
            name="🏆 Top Performers",
            value="\n".join(lines) if lines else "No check-ins yet!",
            inline=False,
        )
        embed.set_footer(
            text="Keep it up! Use /checkin daily to maintain your streak."
        )

        # Find the first writable text channel
        channel = next(
            (
                ch
                for ch in guild.text_channels
                if ch.permissions_for(guild.me).send_messages
            ),
            None,
        )
        if channel is None:
            logger.warning("No writable channel found in guild %d.", guild.id)
            return

        try:
            await channel.send(embed=embed)
            logger.info("Posted weekly report to guild %d (#%s).", guild.id, channel.name)
        except discord.Forbidden:
            logger.warning(
                "No permission to send weekly report in guild %d.", guild.id
            )
