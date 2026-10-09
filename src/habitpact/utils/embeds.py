"""Discord embed builders for consistent styling across commands."""

from __future__ import annotations

import discord

# Brand colors
COLOR_SUCCESS = discord.Colour.from_rgb(87, 242, 135)   # Green
COLOR_ERROR = discord.Colour.from_rgb(237, 66, 69)      # Red
COLOR_INFO = discord.Colour.from_rgb(88, 101, 242)      # Blurple
COLOR_WARNING = discord.Colour.from_rgb(254, 231, 92)   # Yellow
COLOR_STREAK = discord.Colour.from_rgb(250, 168, 26)    # Orange/gold


def success_embed(title: str, description: str) -> discord.Embed:
    """Green embed for successful operations."""
    return discord.Embed(
        title=f"✅ {title}",
        description=description,
        colour=COLOR_SUCCESS,
    )


def error_embed(description: str) -> discord.Embed:
    """Red embed for errors and validation failures."""
    return discord.Embed(
        title="❌ Error",
        description=description,
        colour=COLOR_ERROR,
    )


def info_embed(title: str, description: str = "") -> discord.Embed:
    """Blurple embed for informational responses."""
    return discord.Embed(
        title=title,
        description=description,
        colour=COLOR_INFO,
    )


def warning_embed(description: str) -> discord.Embed:
    """Yellow embed for warnings."""
    return discord.Embed(
        title="⚠️ Warning",
        description=description,
        colour=COLOR_WARNING,
    )
