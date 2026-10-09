"""Stats and leaderboard cog — /stats and /leaderboard commands."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from habitpact.db.engine import get_session
from habitpact.services.guild_service import GuildService
from habitpact.services.stats_service import StatsService
from habitpact.utils.embeds import COLOR_INFO, COLOR_STREAK, error_embed

logger = logging.getLogger(__name__)

RANK_MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}


class StatsCog(commands.Cog):
    """Slash commands for stats and leaderboard."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="stats",
        description="View your personal habit stats and streaks",
    )
    async def stats(self, interaction: discord.Interaction) -> None:
        """Show personal streak stats for all active habits."""
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

            stats_svc = StatsService(session)
            habit_stats = await stats_svc.get_user_stats(user)

            if not habit_stats:
                embed = discord.Embed(
                    title="📊 Your Stats",
                    description=(
                        "You don't have any habits yet.\n"
                        "Use `/habit create <name>` to get started!"
                    ),
                    colour=COLOR_INFO,
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title=f"📊 {interaction.user.display_name}'s Stats",
                colour=COLOR_STREAK,
            )

            total_streak = 0
            total_checkins = 0

            for hs in habit_stats:
                s = hs.streak
                total_streak += s.current_streak
                total_checkins += s.total_checkins

                # Streak indicator emoji
                if s.current_streak >= 30:
                    flame = "🔥🔥🔥"
                elif s.current_streak >= 7:
                    flame = "🔥🔥"
                elif s.current_streak >= 1:
                    flame = "🔥"
                else:
                    flame = "💤"

                embed.add_field(
                    name=f"{flame} {hs.habit_name}",
                    value=(
                        f"Current: **{s.current_streak}d** | "
                        f"Best: **{s.longest_streak}d** | "
                        f"Total: **{s.total_checkins}**"
                    ),
                    inline=False,
                )

            embed.set_footer(
                text=(
                    f"Total active streak days: {total_streak} • "
                    f"Total check-ins: {total_checkins} • "
                    f"Timezone: {user.timezone}"
                )
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="leaderboard",
        description="View the server habit accountability leaderboard",
    )
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        """Show the top 10 guild members by total active streak days."""
        if interaction.guild is None:
            await interaction.response.send_message(
                embed=error_embed("This command can only be used in a server."),
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        async for session in get_session():
            stats_svc = StatsService(session)
            entries = await stats_svc.get_guild_leaderboard(
                guild_id=interaction.guild.id, limit=10
            )

            if not entries:
                embed = discord.Embed(
                    title="🏆 Leaderboard",
                    description=(
                        "No one has checked in yet!\n"
                        "Use `/checkin` to start building your streak."
                    ),
                    colour=COLOR_INFO,
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title=f"🏆 {interaction.guild.name} — Accountability Leaderboard",
                description="Ranked by total active streak days across all habits.",
                colour=discord.Colour.gold(),
            )

            requesting_user_rank: int | None = None
            lines: list[str] = []

            for rank, entry in enumerate(entries, start=1):
                medal = RANK_MEDALS.get(rank, f"**#{rank}**")

                # Try to get the member's display name
                member = interaction.guild.get_member(entry.discord_id)
                name = member.display_name if member else f"User {entry.discord_id}"

                line = (
                    f"{medal} **{name}** — "
                    f"{entry.total_streak} streak day(s) across "
                    f"{entry.habit_count} habit(s)"
                )
                lines.append(line)

                if entry.discord_id == interaction.user.id:
                    requesting_user_rank = rank

            embed.description = "\n".join(lines)

            # Show the requesting user's rank if not in top 10
            if requesting_user_rank is None:
                embed.set_footer(text="You are not yet ranked. Keep checking in!")
            else:
                embed.set_footer(text=f"Your rank: #{requesting_user_rank}")

            await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Register this cog with the bot."""
    await bot.add_cog(StatsCog(bot))
