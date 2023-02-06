"""add post stars

Revision ID: e35650038a94
Revises: 0bb280063612
Create Date: 2023-02-06 12:27:38.710532

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e35650038a94"
down_revision = "0bb280063612"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("post", sa.Column("stars", sa.Integer(), nullable=True))


def downgrade():
    op.drop_column("post", "stars")
