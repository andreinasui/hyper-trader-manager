"""Database bootstrap utilities — runs Alembic migrations on startup.

Handles three cases:
1. Fresh DB (no tables): run `alembic upgrade head` to create everything.
2. Legacy DB (core tables present, no `alembic_version`): stamp at baseline,
   then upgrade to head.
3. Already-migrated DB: just upgrade to head (no-op if already at head).
"""

from __future__ import annotations

import logging
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, inspect

from alembic import command

logger = logging.getLogger(__name__)

BASELINE_REVISION = "0001_baseline"
# Lowest migration revision; this value must NEVER change as we add new migrations.
# It's used to stamp legacy DBs that pre-date alembic at the schema produced by 0001.


def _alembic_config(engine: Engine) -> Config:
    api_root = Path(__file__).resolve().parents[2]
    cfg = Config(str(api_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(api_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    # Prevent alembic from reconfiguring the root logger via fileConfig —
    # doing so would reset log levels and break caplog in tests.
    cfg.attributes["configure_logger"] = False
    return cfg


def _is_legacy_db(engine: Engine) -> bool:
    """A legacy DB has core tables but no alembic_version."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    return "users" in tables and "alembic_version" not in tables


def bootstrap_database(engine: Engine) -> None:
    """Run Alembic migrations, stamping legacy DBs at baseline first."""
    cfg = _alembic_config(engine)

    with engine.connect() as conn:
        # Share one connection across stamp + upgrade so SQLite :memory: DBs see the
        # same schema (each connection sees its own :memory: database). Both alembic
        # commands manage their own transactions on this connection.
        # Inject the connection so env.py reuses it (critical for in-memory SQLite).
        cfg.attributes["connection"] = conn

        if _is_legacy_db(engine):
            logger.info("Detected legacy DB without alembic_version — stamping at baseline")
            command.stamp(cfg, BASELINE_REVISION)

        logger.info("Running alembic upgrade head")
        command.upgrade(cfg, "head")
