"""Tests for database engine error paths and uninitialised state."""

from __future__ import annotations

import pytest

from habitpact.db.engine import close_db, get_engine, get_session_factory, init_db


@pytest.fixture(autouse=True)
async def reset_engine() -> None:  # type: ignore[return]
    """Ensure module-level engine state is clean before and after each test."""
    # Teardown any previous state
    await close_db()
    yield
    await close_db()


class TestEngineErrorPaths:
    """Test that uninitialized engine raises correctly."""

    async def test_get_engine_before_init_raises(self) -> None:
        with pytest.raises(RuntimeError, match="Database not initialized"):
            get_engine()

    async def test_get_session_factory_before_init_raises(self) -> None:
        with pytest.raises(RuntimeError, match="Database not initialized"):
            get_session_factory()


class TestEngineLifecycle:
    """Test init and close lifecycle."""

    async def test_init_db_sqlite(self) -> None:
        await init_db("sqlite+aiosqlite:///:memory:")
        engine = get_engine()
        assert engine is not None
        factory = get_session_factory()
        assert factory is not None

    async def test_close_db_clears_state(self) -> None:
        await init_db("sqlite+aiosqlite:///:memory:")
        await close_db()
        # After closing, should raise again
        with pytest.raises(RuntimeError):
            get_engine()

    async def test_close_db_idempotent(self) -> None:
        """Calling close_db twice should not raise."""
        await init_db("sqlite+aiosqlite:///:memory:")
        await close_db()
        await close_db()  # Should not raise

    async def test_get_session_yields_session(self) -> None:
        from sqlalchemy.ext.asyncio import AsyncSession

        from habitpact.db.engine import get_session

        await init_db("sqlite+aiosqlite:///:memory:")
        async for session in get_session():
            assert isinstance(session, AsyncSession)
