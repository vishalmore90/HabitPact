"""Async database engine setup and session management."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from habitpact.db.models import Base

logger = logging.getLogger(__name__)

# Module-level state — initialized by init_db(), torn down by close_db().
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the current async engine. Raises if not initialized."""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the current session factory. Raises if not initialized."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory


async def init_db(database_url: str) -> None:
    """
    Create the async engine and session factory.

    For dev (SQLite), also creates all tables automatically.
    For prod (PostgreSQL), Alembic migrations should be used instead.
    """
    global _engine, _session_factory

    is_sqlite = database_url.startswith("sqlite")

    _engine = create_async_engine(
        database_url,
        echo=False,
        # SQLite doesn't support pool configuration
        **({"pool_pre_ping": True} if not is_sqlite else {}),
    )

    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Auto-create tables for SQLite (dev convenience)
    if is_sqlite:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("SQLite tables created.")
    else:
        logger.info("PostgreSQL engine ready. Use Alembic for migrations.")


async def close_db() -> None:
    """Dispose of the engine and release all connections."""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database engine disposed.")

    _engine = None
    _session_factory = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session, ensuring it is closed after use."""
    factory = get_session_factory()
    async with factory() as session:
        yield session
