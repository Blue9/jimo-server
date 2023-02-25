"""add media column to post table

Revision ID: 378d78e50715
Revises: 064a2159eb7b
Create Date: 2023-02-25 17:45:38.953122

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "378d78e50715"
down_revision = "064a2159eb7b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("post", sa.Column("media", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    op.drop_column("post", "media")
