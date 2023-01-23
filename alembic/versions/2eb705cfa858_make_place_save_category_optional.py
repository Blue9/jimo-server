"""make place save category optional

Revision ID: 2eb705cfa858
Revises: 345b58ae4a73
Create Date: 2023-01-20 17:55:53.283584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2eb705cfa858"
down_revision = "345b58ae4a73"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("place_save", "category", existing_type=sa.TEXT(), nullable=True)


def downgrade():
    op.alter_column("place_save", "category", existing_type=sa.TEXT(), nullable=False)
