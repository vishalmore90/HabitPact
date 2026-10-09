"""Shared autocomplete callbacks for cogs."""

from __future__ import annotations

import discord
from discord import app_commands

from habitpact.db.engine import get_session
from habitpact.services.guild_service import GuildService
from habitpact.services.habit_service import HabitService


async def habit_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Return autocomplete choices for a user's active habit names.

    Filters by the current partial input (case-insensitive).
    Returns at most 25 results (Discord's limit).
    """
    if interaction.guild is None:
        return []

    async for session in get_session():
        guild_svc = GuildService(session)
        user = await guild_svc.get_or_create_user(
            discord_id=interaction.user.id,
            guild_id=interaction.guild.id,
            guild_name=interaction.guild.name,
        )
        habit_svc = HabitService(session)
        habits = await habit_svc.list_active_habits(user)

    return [
        app_commands.Choice(name=h.name, value=h.name)
        for h in habits
        if current.lower() in h.name.lower()
    ][:25]
