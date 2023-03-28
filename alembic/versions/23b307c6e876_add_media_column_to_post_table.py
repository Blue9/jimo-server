"""add media column to post table

Revision ID: 23b307c6e876
Revises: 064a2159eb7b
Create Date: 2023-03-27 21:05:03.705175

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "23b307c6e876"
down_revision = "064a2159eb7b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "post", sa.Column("media", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False)
    )


def downgrade():
    op.drop_column("post", "media")
