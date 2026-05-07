"""add trader log archives + last_started_at

Revision ID: 0002_add_log_archives
Revises: 0001_baseline
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_add_log_archives"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("traders") as batch:
        batch.add_column(sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "trader_log_archives",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "trader_id",
            sa.String(length=36),
            sa.ForeignKey("traders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("run_ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_trader_log_archives_trader_id",
        "trader_log_archives",
        ["trader_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_trader_log_archives_trader_id", table_name="trader_log_archives")
    op.drop_table("trader_log_archives")
    with op.batch_alter_table("traders") as batch:
        batch.drop_column("last_started_at")
