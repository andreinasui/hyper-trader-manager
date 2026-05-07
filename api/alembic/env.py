"""Alembic environment configured to read URL from app settings."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from hyper_trader_api.config import get_settings
from hyper_trader_api.database import Base

# Import every model module so all tables register with Base.metadata.
# Add new model imports here when introducing new tables.
from hyper_trader_api.models import (
    session_token,  # noqa: F401
    ssl_config,  # noqa: F401
    trader,  # noqa: F401
    user,  # noqa: F401
)

settings = get_settings()

config = context.config
# bootstrap_database() sets cfg.attributes["configure_logger"] = False to suppress
# fileConfig from resetting log levels during programmatic use (tests, app startup).
# Default True preserves normal CLI behaviour.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

# Only fall back to app settings URL if not already set programmatically
# (e.g. bootstrap_database injects the URL via cfg.set_main_option)
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # Required for SQLite ALTER support; no-op on other backends.
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # If a connection was injected by bootstrap_database, use it directly.
    # This avoids creating a second engine (critical for in-memory SQLite).
    # Alembic connection-injection pattern: lets callers (e.g. bootstrap_database)
    # share one Connection across multiple alembic commands. Required for SQLite
    # in-memory DBs since each Connection has its own :memory: instance.
    # See: https://alembic.sqlalchemy.org/en/latest/cookbook.html
    injected_connection = context.config.attributes.get("connection", None)
    if injected_connection is not None:
        context.configure(
            connection=injected_connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER support; no-op on other backends.
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # Required for SQLite ALTER support; no-op on other backends.
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
