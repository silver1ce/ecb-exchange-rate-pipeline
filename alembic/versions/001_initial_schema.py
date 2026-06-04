"""Initial schema for ECB exchange rate pipeline.

Revision ID: 001_initial
Revises:
Create Date: 2026-06-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create normalized OLTP tables for ECB exchange rates."""
    op.create_table(
        "frequency",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=4), nullable=False),
        sa.Column("description", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )

    op.create_table(
        "currency",
        sa.Column("id", sa.SmallInteger(), autoincrement=True, nullable=False),
        sa.Column("iso_code", sa.String(length=3), nullable=False),
        sa.Column("description", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso_code"),
    )

    op.create_table(
        "exchange_rate_series",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("series_key", sa.String(length=64), nullable=False),
        sa.Column("freq_id", sa.SmallInteger(), nullable=False),
        sa.Column("currency_id", sa.SmallInteger(), nullable=False),
        sa.Column("exr_type", sa.String(length=8), nullable=True),
        sa.Column("exr_var", sa.String(length=8), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["currency_id"], ["currency.id"]),
        sa.ForeignKeyConstraint(["freq_id"], ["frequency.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_key"),
    )
    op.create_index("idx_series_currency", "exchange_rate_series", ["currency_id"])
    op.create_index("idx_series_freq", "exchange_rate_series", ["freq_id"])

    op.create_table(
        "exchange_rate_observation",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("series_id", sa.Integer(), nullable=False),
        sa.Column("time_period", sa.Date(), nullable=False),
        sa.Column("obs_value", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("obs_status", sa.String(length=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["series_id"], ["exchange_rate_series.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("series_id", "time_period", name="uq_obs_series_period"),
    )
    op.create_index(
        "idx_obs_series_period",
        "exchange_rate_observation",
        ["series_id", "time_period"],
    )
    op.create_index("idx_obs_time_period", "exchange_rate_observation", ["time_period"])

    op.create_table(
        "ingestion_run",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="running", nullable=False),
        sa.Column("rows_fetched", sa.Integer(), nullable=True),
        sa.Column("rows_inserted", sa.Integer(), nullable=True),
        sa.Column("rows_updated", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("api_url", sa.Text(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all pipeline tables."""
    op.drop_table("ingestion_run")
    op.drop_index("idx_obs_time_period", table_name="exchange_rate_observation")
    op.drop_index("idx_obs_series_period", table_name="exchange_rate_observation")
    op.drop_table("exchange_rate_observation")
    op.drop_index("idx_series_freq", table_name="exchange_rate_series")
    op.drop_index("idx_series_currency", table_name="exchange_rate_series")
    op.drop_table("exchange_rate_series")
    op.drop_table("currency")
    op.drop_table("frequency")
