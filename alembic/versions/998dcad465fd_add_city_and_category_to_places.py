"""add city and category to places

Revision ID: 998dcad465fd
Revises: a35d49e143fd
Create Date: 2023-01-28 17:24:13.907954

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "998dcad465fd"
down_revision = "a35d49e143fd"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("place", sa.Column("city", sa.Text(), nullable=True))
    op.add_column("place", sa.Column("category", sa.Text(), nullable=True))
    op.drop_index("idx_post_custom_location", table_name="post")
    op.drop_column("post", "custom_location")
    op.drop_column("post", "custom_latitude")
    op.drop_column("post", "custom_longitude")


def downgrade():
    # Don't want custom post fields back
    op.drop_column("place", "category")
    op.drop_column("place", "city")
