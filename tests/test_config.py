"""Tests for the config module."""

from __future__ import annotations

import pytest

from habitpact.config import Settings, _normalise_database_url, load_settings


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
        assert s.port is None

    def test_custom_port(self) -> None:
        s = Settings(discord_token="tok", port=8080)
        assert s.port == 8080

    def test_frozen(self) -> None:
        s = Settings(discord_token="tok")
        with pytest.raises(AttributeError):
            s.discord_token = "other"  # type: ignore[misc]

    def test_configure_logging_does_not_raise(self) -> None:
        """configure_logging() should complete without raising."""
        s = Settings(discord_token="tok", log_level="WARNING")
        s.configure_logging()  # Should not raise

    def test_configure_logging_invalid_level_does_not_raise(self) -> None:
        """Invalid log level string should not raise (falls back to INFO)."""
        s = Settings(discord_token="tok", log_level="NOTAVALIDLEVEL")
        s.configure_logging()  # Should not raise


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

    def test_load_settings_custom_log_level(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = load_settings()
        assert settings.log_level == "DEBUG"

    def test_load_settings_prod_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("ENVIRONMENT", "prod")
        settings = load_settings()
        assert settings.is_prod is True

    def test_load_settings_port_parsing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("PORT", "10000")
        settings = load_settings()
        assert settings.port == 10000

    def test_load_settings_invalid_port_ignored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("PORT", "not-a-port")
        settings = load_settings()
        assert settings.port is None


class TestNormaliseDatabaseUrl:
    """Tests for the URL normalisation helper that fixes the Render psycopg error."""

    def test_postgres_scheme_rewritten(self) -> None:
        result = _normalise_database_url("postgres://user:pass@host:5432/db")
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_postgresql_scheme_rewritten(self) -> None:
        result = _normalise_database_url("postgresql://user:pass@host:5432/db")
        assert result == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_asyncpg_scheme_unchanged(self) -> None:
        url = "postgresql+asyncpg://user:pass@host:5432/db"
        assert _normalise_database_url(url) == url

    def test_sqlite_url_unchanged(self) -> None:
        url = "sqlite+aiosqlite:///habitpact.db"
        assert _normalise_database_url(url) == url

    def test_in_memory_sqlite_unchanged(self) -> None:
        url = "sqlite+aiosqlite:///:memory:"
        assert _normalise_database_url(url) == url

    def test_load_settings_rewrites_render_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end: Render-style DATABASE_URL is rewritten at load time."""
        monkeypatch.setenv("DISCORD_TOKEN", "tok")
        monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:5432/habitpact")
        settings = load_settings()
        assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/habitpact"

