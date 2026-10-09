"""Tests for the config module."""

from __future__ import annotations

import pytest

from habitpact.config import Settings, load_settings


class TestSettings:
    """Test the Settings dataclass."""

    def test_is_prod_false_for_dev(self) -> None:
        s = Settings(discord_token="tok", environment="dev")
        assert s.is_prod is False

    def test_is_prod_true_for_prod(self) -> None:
        s = Settings(discord_token="tok", environment="prod")
        assert s.is_prod is True

    def test_defaults(self) -> None:
        s = Settings(discord_token="tok")
        assert s.database_url == "sqlite+aiosqlite:///habitpact.db"
        assert s.log_level == "INFO"
        assert s.environment == "dev"

    def test_frozen(self) -> None:
        s = Settings(discord_token="tok")
        with pytest.raises(AttributeError):
            s.discord_token = "other"  # type: ignore[misc]


class TestLoadSettings:
    """Test loading settings from environment variables."""

    def test_load_settings_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "my-token")
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
        settings = load_settings()
        assert settings.discord_token == "my-token"
        assert settings.database_url == "sqlite+aiosqlite:///:memory:"

    def test_load_settings_missing_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("DISCORD_TOKEN", raising=False)
        with pytest.raises(RuntimeError, match="DISCORD_TOKEN is not set"):
            load_settings()
