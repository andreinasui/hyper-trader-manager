"""baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "traders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("wallet_address", sa.String(length=42), nullable=False, unique=True),
        sa.Column("runtime_name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("start_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(length=1000), nullable=True),
        sa.Column("stopped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("image_tag", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_trader_user_name"),
    )
    op.create_index("ix_traders_user_id", "traders", ["user_id"])
    op.create_index("ix_traders_status", "traders", ["status"])

    op.create_table(
        "trader_configs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "trader_id",
            sa.String(length=36),
            sa.ForeignKey("traders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("trader_id", "version", name="uq_trader_config_version"),
    )

    op.create_table(
        "session_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_session_tokens_user_id", "session_tokens", ["user_id"])
    op.create_index("ix_session_tokens_token_hash", "session_tokens", ["token_hash"])
    op.create_index("ix_session_tokens_expires_at", "session_tokens", ["expires_at"])

    op.create_table(
        "ssl_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("mode", sa.String(length=20), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("configured_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("ssl_config")
    op.drop_index("ix_session_tokens_expires_at", table_name="session_tokens")
    op.drop_index("ix_session_tokens_token_hash", table_name="session_tokens")
    op.drop_index("ix_session_tokens_user_id", table_name="session_tokens")
    op.drop_table("session_tokens")
    op.drop_table("trader_configs")
    op.drop_index("ix_traders_status", table_name="traders")
    op.drop_index("ix_traders_user_id", table_name="traders")
    op.drop_table("traders")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
