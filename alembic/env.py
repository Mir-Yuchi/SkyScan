# alembic/env.py

import asyncio
import logging
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context
from app.core.config import settings
from app.db.base import Base  # our DeclarativeBase

# this is the Alembic Config object
config = context.config
fileConfig(config.config_file_name)

# metadata for 'autogenerate' support (even though we're writing SQL by hand)
target_metadata = Base.metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations_offline() -> None:
    url = str(settings.database_url)
    logger.info(f"Running offline migrations with URL: {url}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(sync_connection) -> None:
    """
    This function is executed in a synchronous context,
    taking the raw DBAPI connection.
    """
    logger.info("Running online migrations")
    context.configure(
        connection=sync_connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable: AsyncEngine = create_async_engine(
        str(settings.database_url),
        poolclass=pool.NullPool,
        future=True,
    )
    logger.info(f"Connecting to database with URL: {str(settings.database_url)}")
    async with connectable.connect() as connection:
        # Pass the sync connection to our runner
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
