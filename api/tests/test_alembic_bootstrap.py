"""Tests for alembic bootstrap shim."""

from __future__ import annotations

import json
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


def _insert_user_and_trader(engine, config: dict) -> str:
    config_id = "9884ab1b-d425-413e-8e8a-114d1223cfbb"
    with engine.connect() as conn:
        conn.execute(
            text(
                """
                INSERT INTO users (id, username, password_hash, is_admin)
                VALUES ('d539c596-d3bd-4285-bac7-68e638efca70', 'testuser', 'hash', 0)
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO traders (
                    id, user_id, wallet_address, runtime_name, status,
                    start_attempts, image_tag
                )
                VALUES (
                    '7107d763-c641-4141-aff1-169a14aecb9b',
                    'd539c596-d3bd-4285-bac7-68e638efca70',
                    '0x3b90beee0f7dba4078d7a1f1d2df37078035a549',
                    'trader-3b90beee',
                    'stopped',
                    1,
                    '0.4.6'
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO trader_configs (id, trader_id, config_json, version)
                VALUES (
                    :id,
                    '7107d763-c641-4141-aff1-169a14aecb9b',
                    :config_json,
                    1
                )
                """
            ),
            {"id": config_id, "config_json": json.dumps(config)},
        )
        conn.commit()
    return config_id


def _read_config(engine, config_id: str) -> dict:
    with engine.connect() as conn:
        value = conn.execute(
            text("SELECT config_json FROM trader_configs WHERE id = :id"),
            {"id": config_id},
        ).scalar_one()
    return json.loads(value) if isinstance(value, str) else value


def _legacy_order_based_config() -> dict:
    return {
        "provider_settings": {
            "exchange": "hyperliquid",
            "network": "mainnet",
            "self_account": {
                "address": "0x3b90beee0f7dba4078d7a1f1d2df37078035a549",
                "is_sub": False,
            },
            "copy_account": {"address": "0xe79d69fd1ed52dd14d7f55155259519ea20d0534"},
            "slippage_bps": 200,
        },
        "trader_settings": {
            "trading_strategy": {
                "type": "order_based",
                "risk_parameters": {
                    "allowed_assets": None,
                    "blocked_assets": [],
                    "max_leverage": None,
                    "self_proportionality_multiplier": 1.0,
                    "open_on_low_pnl": {"enabled": True, "max_pnl": 0.11},
                },
                "bucket_config": {
                    "manual": None,
                    "auto": {
                        "ratio_threshold": 1000.0,
                        "wide_bucket_percent": 0.01,
                        "narrow_bucket_percent": 0.0001,
                    },
                    "pricing_strategy": "vwap",
                },
            }
        },
    }


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


def test_bootstrap_normalizes_legacy_trader_config(tmp_db_url: str) -> None:
    engine = create_engine(tmp_db_url)
    _create_legacy_db(engine)
    config_id = _insert_user_and_trader(engine, _legacy_order_based_config())

    bootstrap_database(engine)

    config = _read_config(engine, config_id)
    provider_risk = config["provider_settings"]["risk_parameters"]
    strategy = config["trader_settings"]["trading_strategy"]
    strategy_risk = strategy["risk_parameters"]
    bucket = strategy["bucket_config"]
    assert provider_risk == {
        "allowed_assets": "*",
        "blocked_assets": [],
        "max_leverage": None,
    }
    assert strategy_risk == {
        "self_proportionality_multiplier": 1.0,
        "open_on_low_pnl": {"enabled": True, "max_pnl": 0.11},
    }
    assert bucket == {
        "type": "auto",
        "ratio_threshold": 1000.0,
        "wide_bucket_percent": 0.01,
        "narrow_bucket_percent": 0.0001,
        "pricing_strategy": "vwap",
    }


def test_bootstrap_defaults_empty_allowed_assets_list_in_trader_config(
    tmp_db_url: str,
) -> None:
    engine = create_engine(tmp_db_url)
    _create_legacy_db(engine)
    legacy_config = _legacy_order_based_config()
    legacy_config["trader_settings"]["trading_strategy"]["risk_parameters"][
        "allowed_assets"
    ] = []
    config_id = _insert_user_and_trader(engine, legacy_config)

    bootstrap_database(engine)

    config = _read_config(engine, config_id)
    assert config["provider_settings"]["risk_parameters"]["allowed_assets"] == "*"


def test_bootstrap_leaves_current_trader_config_unchanged(tmp_db_url: str) -> None:
    engine = create_engine(tmp_db_url)
    _create_legacy_db(engine)
    current_config = _legacy_order_based_config()
    provider = current_config["provider_settings"]
    strategy = current_config["trader_settings"]["trading_strategy"]
    provider["risk_parameters"] = {
        "allowed_assets": "*",
        "blocked_assets": [],
        "max_leverage": None,
    }
    strategy["risk_parameters"] = {
        "self_proportionality_multiplier": 1.0,
        "open_on_low_pnl": {"enabled": True, "max_pnl": 0.11},
    }
    strategy["bucket_config"] = {
        "type": "auto",
        "ratio_threshold": 1000.0,
        "wide_bucket_percent": 0.01,
        "narrow_bucket_percent": 0.0001,
        "pricing_strategy": "vwap",
    }
    config_id = _insert_user_and_trader(engine, current_config)

    bootstrap_database(engine)

    assert _read_config(engine, config_id) == current_config
