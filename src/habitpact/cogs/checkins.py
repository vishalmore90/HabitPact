"""Check-in cog — /checkin command."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from habitpact.db.engine import get_session
from habitpact.services.checkin_service import CheckinService
from habitpact.services.guild_service import GuildService
from habitpact.services.habit_service import HabitService
from habitpact.utils.autocomplete import habit_name_autocomplete
from habitpact.utils.embeds import COLOR_STREAK, error_embed, success_embed

logger = logging.getLogger(__name__)

MILESTONE_MESSAGES = {
    7: "One week strong! 🔥 You're building real momentum!",
    14: "Two weeks! 💪 That's a genuine habit now!",
    30: "30 days! 🌟 A whole month of consistency!",
    60: "60 days! 🚀 You're absolutely unstoppable!",
    100: "100 DAYS! 🏆 That is legendary discipline!",
    200: "200 days! 🎖️ You are an inspiration!",
    365: "365 days! 👑 A FULL YEAR. Unbelievable!",
}


class CheckinCog(commands.Cog):
    """Slash commands for daily check-ins."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="checkin",
        description="Check in for one of your habits today",
    )
    @app_commands.describe(habit="The name of the habit to check in for")
    @app_commands.autocomplete(habit=habit_name_autocomplete)
    async def checkin(self, interaction: discord.Interaction, habit: str) -> None:
        """Record a daily check-in for a habit."""
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error_embed("This command can only be used in a server."),
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

            # Find the habit
            habit_svc = HabitService(session)
            found_habit = await habit_svc._find_active_habit(user.id, habit.strip())

            if found_habit is None:
                await interaction.response.send_message(
                    embed=error_embed(
                        f"No active habit found called **{habit}**.\n"
                        "Use `/habit list` to see your habits."
                    ),
                    ephemeral=True,
                )
                return

            # Perform check-in
            checkin_svc = CheckinService(session)
            result = await checkin_svc.perform_checkin(found_habit, user.timezone)

            if not result.success:
                await interaction.response.send_message(
                    embed=error_embed(result.message), ephemeral=True
                )
                return

            # Build the response embed
            streak = result.streak
            assert streak is not None

            if streak.is_milestone:
                # Special milestone embed
                milestone_msg = MILESTONE_MESSAGES.get(
                    streak.current_streak,
                    f"🏆 **{streak.current_streak} day milestone!**",
                )
                embed = discord.Embed(
                    title=f"🏆 MILESTONE: {streak.current_streak} Days!",
                    description=(
                        f"Checked in for **{found_habit.name}**!\n\n"
                        f"{milestone_msg}"
                    ),
                    colour=discord.Colour.gold(),
                )
            else:
                embed = success_embed(
                    "Checked In!",
                    f"Logged **{found_habit.name}** for today.",
                )
                embed.colour = COLOR_STREAK

            # Add streak fields
            embed.add_field(
                name="🔥 Current Streak",
                value=f"**{streak.current_streak}** day(s)",
                inline=True,
            )
            embed.add_field(
                name="🏅 Longest Streak",
                value=f"**{streak.longest_streak}** day(s)",
                inline=True,
            )
            embed.add_field(
                name="📅 Total Check-ins",
                value=f"**{streak.total_checkins}**",
                inline=True,
            )
            embed.set_footer(
                text=f"Timezone: {user.timezone} • Keep it up, {interaction.user.display_name}!"
            )

            await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Register this cog with the bot."""
    await bot.add_cog(CheckinCog(bot))
