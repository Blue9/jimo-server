"""add place save category and note

Revision ID: 345b58ae4a73
Revises: a229b4dc25c7
Create Date: 2023-01-18 17:52:41.315961

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "345b58ae4a73"
down_revision = "a229b4dc25c7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("place_save", sa.Column("category", sa.Text(), nullable=False))
    op.add_column("place_save", sa.Column("note", sa.Text(), nullable=False))
    op.create_foreign_key(None, "place_save", "category", ["category"], ["name"])


def downgrade():
    op.drop_column("place_save", "note")
    op.drop_column("place_save", "category")
