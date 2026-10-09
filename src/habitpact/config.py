"""Application configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _find_dotenv() -> Path | None:
    """Walk up from CWD to find a .env file."""
    current = Path.cwd()
    for parent in [current, *current.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


@dataclass(frozen=True)
class Settings:
    """Immutable application settings parsed from environment variables."""

    discord_token: str
    database_url: str = "sqlite+aiosqlite:///habitpact.db"
    log_level: str = "INFO"
    environment: str = "dev"

    # Derived
    is_prod: bool = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "is_prod", self.environment.lower() == "prod")

    def configure_logging(self) -> None:
        """Set up structured logging based on the configured log level."""
        numeric_level = getattr(logging, self.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def load_settings() -> Settings:
    """Load settings from environment variables, with .env file support."""
    dotenv_path = _find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path)

    token = os.environ.get("DISCORD_TOKEN", "")
    if not token:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. "
            "Copy .env.example to .env and fill in your bot token."
        )

    return Settings(
        discord_token=token,
        database_url=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///habitpact.db"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        environment=os.environ.get("ENVIRONMENT", "dev"),
    )
