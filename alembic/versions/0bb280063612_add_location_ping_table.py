"""add location ping table

Revision ID: 0bb280063612
Revises: 812e3bffe118
Create Date: 2023-02-01 15:20:00.978148

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0bb280063612"
down_revision = "812e3bffe118"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "location",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("uid", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("location")
