"""Async SQLAlchemy engine + session factory for the QueryMind metadata DB.

This module owns the *single* process-wide engine. Routes obtain a session
through the ``get_db`` FastAPI dependency, which yields a fresh session per
request and guarantees cleanup on both success and exception paths.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# `pool_pre_ping=True` adds a cheap SELECT 1 before each checkout; this is the
# standard fix for stale connections after long-idle periods (e.g. between
# pgbouncer reconnects). The cost is one round-trip per checkout.
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

# `expire_on_commit=False` keeps loaded ORM attributes usable after the
# implicit commit FastAPI does at the end of a request, which is the pattern
# our API routes rely on.
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield a session, close it on exit."""
    async with AsyncSessionLocal() as session:
        yield session


__all__ = ["engine", "AsyncSessionLocal", "get_db"]
