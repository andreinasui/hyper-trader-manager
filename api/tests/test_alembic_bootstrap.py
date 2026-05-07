"""Tests for alembic bootstrap shim."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from hyper_trader_api.db.bootstrap import bootstrap_database


@pytest.fixture
def tmp_db_url(tmp_path: Path) -> str:
    return f"sqlite:///{tmp_path / 'test.db'}"


def _create_legacy_db(engine) -> None:
    """Simulate a pre-alembic legacy DB at the 0001_baseline schema level.

    Creates core tables via alembic up to 0001_baseline, then drops
    alembic_version to mimic a DB created by the old create_all before
    migrations were introduced.
    """
    from pathlib import Path as _Path

    from alembic.config import Config

    from alembic import command

    api_root = _Path(__file__).resolve().parents[1]
    cfg = Config(str(api_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(api_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    cfg.attributes["configure_logger"] = False

    with engine.connect() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0001_baseline")

    # Drop alembic_version to simulate legacy DB (no alembic tracking)
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE alembic_version"))
        conn.commit()


def test_bootstrap_fresh_db_runs_all_migrations(tmp_db_url: str) -> None:
    engine = create_engine(tmp_db_url)
    bootstrap_database(engine)

    insp = inspect(engine)
    tables = set(insp.get_table_names())
    assert "alembic_version" in tables
    assert "users" in tables
    assert "traders" in tables


def test_bootstrap_fresh_db_creates_log_archives_table(tmp_db_url: str) -> None:
    engine = create_engine(tmp_db_url)
    bootstrap_database(engine)

    insp = inspect(engine)
    assert "trader_log_archives" in insp.get_table_names()


def test_bootstrap_legacy_db_stamps_baseline(tmp_db_url: str) -> None:
    """A DB created by old create_all must be stamped at baseline before upgrade."""
    engine = create_engine(tmp_db_url)
    # Simulate legacy: create core tables at 0001 schema, no alembic_version
    _create_legacy_db(engine)

    # Confirm no alembic_version yet
    insp = inspect(engine)
    assert "alembic_version" not in insp.get_table_names()
    assert "users" in insp.get_table_names()

    bootstrap_database(engine)

    insp = inspect(engine)
    assert "alembic_version" in insp.get_table_names()


def test_bootstrap_legacy_db_creates_log_archives_table(tmp_db_url: str) -> None:
    """After stamping legacy DB at baseline and upgrading, 0002 tables must exist."""
    engine = create_engine(tmp_db_url)
    # Simulate legacy: create core tables at 0001 schema, no alembic_version
    _create_legacy_db(engine)
    bootstrap_database(engine)

    insp = inspect(engine)
    assert "trader_log_archives" in insp.get_table_names()
