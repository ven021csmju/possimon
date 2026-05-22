"""wine sommelier fields

Revision ID: a1b2c3d4e5f6
Revises: c2a3ee6f4ec9
Create Date: 2026-05-22

"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "614dfea39bc4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("wines", sa.Column("food_pairing", sa.String(500), nullable=True))
    op.add_column("wines", sa.Column("sweetness", sa.Integer(), nullable=True))
    op.add_column("wines", sa.Column("bottle_size_ml", sa.Integer(), nullable=True, server_default="750"))
    op.add_column("wines", sa.Column("tasting_notes", sa.Text(), nullable=True))
    op.add_column("wines", sa.Column("aging_notes", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("wines", "aging_notes")
    op.drop_column("wines", "tasting_notes")
    op.drop_column("wines", "bottle_size_ml")
    op.drop_column("wines", "sweetness")
    op.drop_column("wines", "food_pairing")
