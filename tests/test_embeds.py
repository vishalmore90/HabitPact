"""Tests for embed utility builders."""

from __future__ import annotations

import discord

from habitpact.utils.embeds import (
    COLOR_ERROR,
    COLOR_INFO,
    COLOR_SUCCESS,
    COLOR_WARNING,
    error_embed,
    info_embed,
    success_embed,
    warning_embed,
)


class TestEmbeds:
    """Test that embed builders produce correctly structured embeds."""

    def test_success_embed_title(self) -> None:
        embed = success_embed("Done", "It worked.")
        assert "Done" in embed.title
        assert embed.description == "It worked."

    def test_success_embed_has_checkmark(self) -> None:
        embed = success_embed("Done", "It worked.")
        assert "✅" in embed.title

    def test_success_embed_colour(self) -> None:
        embed = success_embed("Done", "msg")
        assert embed.colour == COLOR_SUCCESS

    def test_error_embed_title(self) -> None:
        embed = error_embed("Something broke.")
        assert embed.title == "❌ Error"
        assert embed.description == "Something broke."

    def test_error_embed_colour(self) -> None:
        embed = error_embed("msg")
        assert embed.colour == COLOR_ERROR

    def test_info_embed_title(self) -> None:
        embed = info_embed("Info Title", "Info body.")
        assert embed.title == "Info Title"
        assert embed.description == "Info body."

    def test_info_embed_empty_description(self) -> None:
        embed = info_embed("Title only")
        assert embed.title == "Title only"
        assert embed.description == ""

    def test_info_embed_colour(self) -> None:
        embed = info_embed("T", "D")
        assert embed.colour == COLOR_INFO

    def test_warning_embed_title(self) -> None:
        embed = warning_embed("Watch out!")
        assert "⚠️" in embed.title
        assert embed.description == "Watch out!"

    def test_warning_embed_colour(self) -> None:
        embed = warning_embed("msg")
        assert embed.colour == COLOR_WARNING

    def test_embed_returns_discord_embed(self) -> None:
        """Ensure all builders return proper discord.Embed instances."""
        assert isinstance(success_embed("T", "D"), discord.Embed)
        assert isinstance(error_embed("D"), discord.Embed)
        assert isinstance(info_embed("T"), discord.Embed)
        assert isinstance(warning_embed("D"), discord.Embed)
