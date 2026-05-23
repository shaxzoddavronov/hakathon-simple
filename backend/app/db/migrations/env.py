"""Alembic environment for the QueryMind metadata DB (async-aware).

Overrides ``sqlalchemy.url`` from ``Settings.DATABASE_URL`` so the
``alembic.ini`` file does not need to carry the secret. ``Base.metadata``
is imported AFTER models so every table is registered before autogenerate
runs.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.db import Base

# Import models so their tables are registered on `Base.metadata`. Star
# import is intentional here — Alembic needs every model module loaded.
from app.db import models  # noqa: F401

# Alembic Config object — provides access to values within the .ini file.
config = context.config

# Inject the runtime DB URL.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure Python logging if a [loggers] section is present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Emits SQL to stdout instead of running it; useful for generating
    deploy scripts without DB access.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Sync callback executed inside the async transaction."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Build an async engine from `alembic.ini`, then run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point invoked by Alembic in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
