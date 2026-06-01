"""Alembic environment for packages/db.

The database URL is resolved from the environment, never hardcoded:

1. ``DATABASE_URL`` if set (takes precedence), otherwise
2. assembled from ``DB_USER`` / ``DB_PASSWORD`` / ``DB_HOST`` / ``DB_PORT`` /
   ``DB_NAME`` — the same variables apps/api uses (see app/core/config.py).

Both online (live connection) and offline (``--sql``) modes are supported so the
baseline can be reviewed/emitted as SQL without touching a database.
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic Config object, providing access to alembic.ini values.
config = context.config

# Configure logging from alembic.ini if a config file is present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No SQLAlchemy metadata is wired in: the baseline mirrors init.sql by hand and
# future revisions are authored explicitly, so autogenerate is intentionally off.
target_metadata = None


def _database_url() -> str:
    """Resolve the DB URL from the environment.

    Returns:
        A SQLAlchemy/psycopg2 connection URL.

    Raises:
        RuntimeError: if neither DATABASE_URL nor the DB_* parts are provided.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    parts = {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "name": os.getenv("DB_NAME"),
    }
    missing = [k for k, v in parts.items() if not v]
    if missing:
        raise RuntimeError(
            "Database URL is not configured. Set DATABASE_URL, or all of "
            "DB_USER/DB_PASSWORD/DB_HOST/DB_PORT/DB_NAME. "
            f"Missing: {', '.join(missing)}"
        )
    return (
        f"postgresql://{parts['user']}:{parts['password']}"
        f"@{parts['host']}:{parts['port']}/{parts['name']}"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against a live connection)."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
