"""normalize legacy trader configs

Revision ID: 0003_normalize_legacy_trader_configs
Revises: 0002_add_log_archives
Create Date: 2026-06-30
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "0003_normalize_legacy_trader_configs"
down_revision: str | None = "0002_add_log_archives"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _load_config(value: Any) -> dict[str, Any]:
    return json.loads(value) if isinstance(value, str) else value


def _normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    provider = config.get("provider_settings")
    strategy = (config.get("trader_settings") or {}).get("trading_strategy")
    if not isinstance(provider, dict) or not isinstance(strategy, dict):
        return config

    risk = strategy.get("risk_parameters")
    if "risk_parameters" not in provider and isinstance(risk, dict):
        allowed_assets = risk.pop("allowed_assets", None)
        provider["risk_parameters"] = {
            "allowed_assets": allowed_assets or "*",
            "blocked_assets": risk.pop("blocked_assets", []),
            "max_leverage": risk.pop("max_leverage", None),
        }

    bucket = strategy.get("bucket_config")
    if isinstance(bucket, dict) and "type" not in bucket:
        selected = "manual" if bucket.get("manual") is not None else "auto"
        selected_config = bucket.get(selected) or {}
        strategy["bucket_config"] = {
            "type": selected,
            **selected_config,
            "pricing_strategy": bucket.get("pricing_strategy", "vwap"),
        }

    return config


def upgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, config_json FROM trader_configs")).mappings()
    for row in rows:
        config = _load_config(row["config_json"])
        original = json.dumps(config, sort_keys=True)
        normalized = _normalize_config(config)
        if json.dumps(normalized, sort_keys=True) != original:
            conn.execute(
                sa.text("UPDATE trader_configs SET config_json = :config_json WHERE id = :id"),
                {"id": row["id"], "config_json": json.dumps(normalized)},
            )


def downgrade() -> None:
    pass
