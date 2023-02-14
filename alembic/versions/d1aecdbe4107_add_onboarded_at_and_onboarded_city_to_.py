"""add onboarded_at and onboarded_city to user

Revision ID: d1aecdbe4107
Revises: 9c81d4344132
Create Date: 2023-02-14 12:37:07.034503

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d1aecdbe4107"
down_revision = "9c81d4344132"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user", sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("user", sa.Column("onboarded_city", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("user", "onboarded_city")
    op.drop_column("user", "onboarded_at")
