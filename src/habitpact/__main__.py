"""Entry point for running the HabitPact bot."""

from habitpact.bot import create_bot
from habitpact.config import load_settings


def main() -> None:
    """Load config and start the bot."""
    settings = load_settings()
    settings.configure_logging()

    bot = create_bot(settings)
    bot.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
