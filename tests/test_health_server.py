"""Tests for the HTTP health check server used by hosting platforms."""

from __future__ import annotations

import aiohttp
import pytest

from habitpact.bot import HabitPactBot
from habitpact.config import Settings


@pytest.mark.asyncio
async def test_health_server_endpoints() -> None:
    """Test that the health check server starts and returns 200 OK for / and /health."""
    # Use a high random test port
    test_port = 19876
    settings = Settings(discord_token="fake_token", port=test_port)
    bot = HabitPactBot(settings)

    await bot._start_health_server(test_port)

    try:
        async with aiohttp.ClientSession() as session:
            # Test /
            async with session.get(f"http://127.0.0.1:{test_port}/") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["status"] == "healthy"
                assert data["service"] == "habitpact"

            # Test /health
            async with session.get(f"http://127.0.0.1:{test_port}/health") as resp:
                assert resp.status == 200
                data = await resp.json()
                assert data["status"] == "healthy"
                assert data["service"] == "habitpact"
    finally:
        if bot._web_runner is not None:
            await bot._web_runner.cleanup()
