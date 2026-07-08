"""log lifecycle stats tables

Revision ID: 20260708_0001
Revises: a1b2c3d4e5f6
Create Date: 2026-07-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260708_0001"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_user_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stat_date", "user_id", "event_type", "product_id", name="uq_daily_user_stats_key"),
    )
    op.create_index(op.f("ix_daily_user_stats_id"), "daily_user_stats", ["id"], unique=False)
    op.create_index(op.f("ix_daily_user_stats_stat_date"), "daily_user_stats", ["stat_date"], unique=False)
    op.create_index(op.f("ix_daily_user_stats_user_id"), "daily_user_stats", ["user_id"], unique=False)
    op.create_index(op.f("ix_daily_user_stats_event_type"), "daily_user_stats", ["event_type"], unique=False)
    op.create_index(op.f("ix_daily_user_stats_product_id"), "daily_user_stats", ["product_id"], unique=False)

    op.create_table(
        "daily_search_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False),
        sa.Column("keyword", sa.String(length=255), nullable=False),
        sa.Column("normalized_keyword", sa.String(length=255), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("search_count", sa.Integer(), nullable=False),
        sa.Column("total_results", sa.Integer(), nullable=False),
        sa.Column("avg_results", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stat_date", "normalized_keyword", "user_id", name="uq_daily_search_stats_key"),
    )
    op.create_index(op.f("ix_daily_search_stats_id"), "daily_search_stats", ["id"], unique=False)
    op.create_index(op.f("ix_daily_search_stats_stat_date"), "daily_search_stats", ["stat_date"], unique=False)
    op.create_index(
        op.f("ix_daily_search_stats_normalized_keyword"),
        "daily_search_stats",
        ["normalized_keyword"],
        unique=False,
    )
    op.create_index(op.f("ix_daily_search_stats_user_id"), "daily_search_stats", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_daily_search_stats_user_id"), table_name="daily_search_stats")
    op.drop_index(op.f("ix_daily_search_stats_normalized_keyword"), table_name="daily_search_stats")
    op.drop_index(op.f("ix_daily_search_stats_stat_date"), table_name="daily_search_stats")
    op.drop_index(op.f("ix_daily_search_stats_id"), table_name="daily_search_stats")
    op.drop_table("daily_search_stats")

    op.drop_index(op.f("ix_daily_user_stats_product_id"), table_name="daily_user_stats")
    op.drop_index(op.f("ix_daily_user_stats_event_type"), table_name="daily_user_stats")
    op.drop_index(op.f("ix_daily_user_stats_user_id"), table_name="daily_user_stats")
    op.drop_index(op.f("ix_daily_user_stats_stat_date"), table_name="daily_user_stats")
    op.drop_index(op.f("ix_daily_user_stats_id"), table_name="daily_user_stats")
    op.drop_table("daily_user_stats")
