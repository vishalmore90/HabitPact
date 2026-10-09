"""Admin cog — /setup timezone and /remind commands."""

from __future__ import annotations

import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands

from habitpact.db.engine import get_session
from habitpact.services.guild_service import GuildService
from habitpact.utils.embeds import error_embed, info_embed, success_embed
from habitpact.utils.timezone import is_valid_timezone

logger = logging.getLogger(__name__)

TIMEZONE_EXAMPLES = "`Asia/Kolkata`, `US/Eastern`, `Europe/London`, `UTC`"


class AdminCog(commands.Cog):
    """Slash commands for user configuration."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    setup_group = app_commands.Group(
        name="setup", description="Configure your HabitPact settings"
    )

    @setup_group.command(
        name="timezone",
        description="Set your timezone for accurate streak tracking",
    )
    @app_commands.describe(
        timezone="Your IANA timezone (e.g. Asia/Kolkata, US/Eastern, UTC)"
    )
    async def setup_timezone(
        self, interaction: discord.Interaction, timezone: str
    ) -> None:
        """Set the user's timezone."""
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error_embed("This command can only be used in a server."),
                ephemeral=True,
            )
            return

        tz = timezone.strip()

        if not is_valid_timezone(tz):
            await interaction.response.send_message(
                embed=error_embed(
                    f"**{tz}** is not a valid timezone.\n\n"
                    f"Examples: {TIMEZONE_EXAMPLES}\n\n"
                    "Find your timezone at: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
                ),
                ephemeral=True,
            )
            return

        async for session in get_session():
            guild_svc = GuildService(session)
            user = await guild_svc.get_or_create_user(
                discord_id=interaction.user.id,
                guild_id=interaction.guild.id,
                guild_name=interaction.guild.name,
            )
            await guild_svc.update_timezone(user, tz)

        embed = success_embed(
            "Timezone Updated",
            f"Your timezone is now set to **{tz}**.\n\n"
            "Your streaks will now be calculated based on midnight in your local timezone.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="remind",
        description="Set a daily reminder for your habits (or disable it)",
    )
    @app_commands.describe(
        time=(
            "Time in HH:MM format (e.g. 09:00), or 'off' to disable reminders"
        )
    )
    async def remind(self, interaction: discord.Interaction, time: str) -> None:
        """Set or disable a daily DM reminder."""
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error_embed("This command can only be used in a server."),
                ephemeral=True,
            )
            return

        time_str = time.strip().lower()

        # Handle disable
        if time_str == "off":
            async for session in get_session():
                guild_svc = GuildService(session)
                user = await guild_svc.get_or_create_user(
                    discord_id=interaction.user.id,
                    guild_id=interaction.guild.id,
                    guild_name=interaction.guild.name,
                )
                await guild_svc.update_reminder(user, None)

            await interaction.response.send_message(
                embed=info_embed(
                    "Reminders Disabled",
                    "You will no longer receive daily habit reminders.",
                ),
                ephemeral=True,
            )
            return

        # Parse HH:MM
        remind_time = _parse_time(time_str)
        if remind_time is None:
            await interaction.response.send_message(
                embed=error_embed(
                    f"**{time}** is not a valid time format.\n\n"
                    "Use **HH:MM** (24-hour), e.g. `09:00`, `20:30`.\n"
                    "To disable reminders, use `/remind off`."
                ),
                ephemeral=True,
            )
            return

        async for session in get_session():
            guild_svc = GuildService(session)
            user = await guild_svc.get_or_create_user(
                discord_id=interaction.user.id,
                guild_id=interaction.guild.id,
                guild_name=interaction.guild.name,
            )
            await guild_svc.update_reminder(user, remind_time)
            tz = user.timezone

        embed = success_embed(
            "Reminder Set",
            f"You'll receive a daily DM reminder at **{remind_time.strftime('%H:%M')}** "
            f"({tz}).\n\n"
            "Make sure your DMs are open so I can reach you! "
            "Use `/remind off` to disable at any time.",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


def _parse_time(time_str: str) -> datetime.time | None:
    """Parse a HH:MM string into a datetime.time, or return None on failure."""
    try:
        parts = time_str.split(":")
        if len(parts) != 2:
            return None
        hour, minute = int(parts[0]), int(parts[1])
        return datetime.time(hour, minute)
    except (ValueError, IndexError):
        return None


async def setup(bot: commands.Bot) -> None:
    """Register this cog with the bot."""
    await bot.add_cog(AdminCog(bot))
