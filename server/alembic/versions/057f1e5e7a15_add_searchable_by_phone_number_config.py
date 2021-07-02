"""add searchable by phone number config

Revision ID: 057f1e5e7a15
Revises: d556a5d2d28e
Create Date: 2021-07-02 16:52:17.535485

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '057f1e5e7a15'
down_revision = 'd556a5d2d28e'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('preferences',
                  sa.Column('searchable_by_phone_number', sa.Boolean(), server_default=sa.text('true'), nullable=False))


def downgrade():
    op.drop_column('preferences', 'searchable_by_phone_number')
