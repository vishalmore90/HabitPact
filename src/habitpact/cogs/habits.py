"""Habit management cog — /habit create, /habit list, /habit delete."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from habitpact.db.engine import get_session
from habitpact.services.guild_service import GuildService
from habitpact.services.habit_service import HabitService
from habitpact.utils.embeds import error_embed, info_embed, success_embed

logger = logging.getLogger(__name__)


class HabitCog(commands.Cog):
    """Slash commands for managing habits."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    habit_group = app_commands.Group(
        name="habit", description="Manage your habits"
    )

    @habit_group.command(name="create", description="Create a new habit to track")
    @app_commands.describe(name="Name of the habit (e.g., 'Read 30 minutes')")
    async def habit_create(
        self, interaction: discord.Interaction, name: str
    ) -> None:
        """Create a new habit."""
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

            habit_svc = HabitService(session)
            result = await habit_svc.create_habit(user, name)

            if isinstance(result, str):
                await interaction.response.send_message(
                    embed=error_embed(result), ephemeral=True
                )
            else:
                embed = success_embed(
                    "Habit Created",
                    f"**{result.name}** has been added to your habits!",
                )
                embed.add_field(
                    name="Next Step",
                    value=f"Use `/checkin {result.name}` to check in daily.",
                    inline=False,
                )
                await interaction.response.send_message(embed=embed)

    @habit_group.command(name="list", description="List all your active habits")
    async def habit_list(self, interaction: discord.Interaction) -> None:
        """List all active habits for the user."""
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

            habit_svc = HabitService(session)
            habits = await habit_svc.list_active_habits(user)

            if not habits:
                embed = info_embed(
                    "📋 Your Habits",
                    "You don't have any habits yet.\n"
                    "Use `/habit create <name>` to get started!",
                )
            else:
                lines = []
                for i, habit in enumerate(habits, start=1):
                    created = habit.created_at.strftime("%Y-%m-%d") if habit.created_at else "?"
                    lines.append(f"**{i}.** {habit.name} — since {created}")

                embed = info_embed(
                    f"📋 Your Habits ({len(habits)}/5)",
                    "\n".join(lines),
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @habit_group.command(name="delete", description="Delete a habit")
    @app_commands.describe(name="Name of the habit to delete")
    async def habit_delete(
        self, interaction: discord.Interaction, name: str
    ) -> None:
        """Soft-delete a habit by name."""
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

            habit_svc = HabitService(session)
            result = await habit_svc.delete_habit(user, name)

            if isinstance(result, str):
                await interaction.response.send_message(
                    embed=error_embed(result), ephemeral=True
                )
            else:
                embed = success_embed(
                    "Habit Deleted",
                    f"**{result.name}** has been removed from your active habits.\n"
                    "Your historical check-in data has been preserved.",
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Register this cog with the bot."""
    await bot.add_cog(HabitCog(bot))
