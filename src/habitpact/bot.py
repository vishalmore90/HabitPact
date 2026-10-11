"""Bot setup, lifecycle management, and event handlers."""

from __future__ import annotations

import logging

import discord
from aiohttp import web
from discord.ext import commands

from habitpact.config import Settings
from habitpact.db.engine import close_db, init_db
from habitpact.scheduler.tasks import HabitScheduler

logger = logging.getLogger(__name__)

# Extensions (cogs) to load on startup
EXTENSIONS = [
    "habitpact.cogs.habits",
    "habitpact.cogs.checkins",
    "habitpact.cogs.stats",
    "habitpact.cogs.admin",
]


class HabitPactBot(commands.Bot):
    """Custom bot class with database lifecycle management."""

    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = False  # Not needed for MVP

        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )
        self.settings = settings
        self.scheduler = HabitScheduler(self)
        self._web_runner: web.AppRunner | None = None
        self._web_site: web.TCPSite | None = None

    async def _start_health_server(self, port: int) -> None:
        """Start a minimal HTTP server for hosting platform health checks."""
        app = web.Application()

        async def health_check(_request: web.Request) -> web.Response:
            return web.json_response(
                {
                    "status": "healthy",
                    "service": "habitpact",
                    "ready": self.is_ready(),
                }
            )

        app.router.add_get("/", health_check)
        app.router.add_get("/health", health_check)

        self._web_runner = web.AppRunner(app)
        await self._web_runner.setup()
        self._web_site = web.TCPSite(self._web_runner, "0.0.0.0", port)
        await self._web_site.start()
        logger.info("Health check server listening on 0.0.0.0:%d", port)

    async def setup_hook(self) -> None:
        """Called before the bot connects. Initialize DB, health server, and load cogs."""
        # Initialize database
        await init_db(self.settings.database_url)
        logger.info("Database initialized.")

        # Start health check server if PORT is configured (e.g. Render web service)
        if self.settings.port is not None:
            await self._start_health_server(self.settings.port)

        # Load extensions
        for ext in EXTENSIONS:
            await self.load_extension(ext)
            logger.info("Loaded extension: %s", ext)

        # Sync slash commands globally
        synced = await self.tree.sync()
        logger.info("Synced %d slash command(s).", len(synced))

        # Start background scheduler
        self.scheduler.start()

    async def on_ready(self) -> None:
        """Called when the bot is fully connected and ready."""
        assert self.user is not None
        logger.info("Logged in as %s (ID: %d)", self.user.name, self.user.id)
        logger.info("Connected to %d guild(s).", len(self.guilds))

        # Set presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="your habits | /habit create",
        )
        await self.change_presence(activity=activity)

    async def close(self) -> None:
        """Graceful shutdown: stop scheduler, health server, then close DB."""
        self.scheduler.stop()
        if self._web_runner is not None:
            await self._web_runner.cleanup()
            logger.info("Health check server stopped.")
        await close_db()
        logger.info("Database closed.")
        await super().close()


def create_bot(settings: Settings) -> HabitPactBot:
    """Factory function to create a configured bot instance."""
    return HabitPactBot(settings)
