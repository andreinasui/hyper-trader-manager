"""
Database bootstrap utilities.

Creates all tables in SQLite on application startup.
"""

from sqlalchemy import Engine

from hyper_trader_api.database import Base


def bootstrap_database(engine: Engine) -> None:
    """
    Create all database tables.

    This is used for SQLite deployments where we don't have
    separate migration tools. In production, this should be run once
    during initial setup.

    Args:
        engine: SQLAlchemy engine to use for table creation.
    """
    # Import all models to ensure they're registered with Base.metadata
    from hyper_trader_api.models import (  # noqa: F401
        Trader,
        TraderConfig,
        User,
    )
    from hyper_trader_api.models.session_token import SessionToken  # noqa: F401
    from hyper_trader_api.models.ssl_config import SSLConfig  # noqa: F401
    from hyper_trader_api.models.trader import TraderSecret  # noqa: F401

    # Create all tables
    Base.metadata.create_all(bind=engine)
