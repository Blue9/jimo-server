"""add relation field to follow table

Revision ID: f48d046d6b87
Revises: e134475a36ec
Create Date: 2021-04-24 23:29:15.841364

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f48d046d6b87'
down_revision = 'e134475a36ec'
branch_labels = None
depends_on = None


def upgrade():
    user_relation_type = postgresql.ENUM('following', 'blocked', name='user_relation_type')
    user_relation_type.create(op.get_bind())
    op.add_column('follow', sa.Column('relation', user_relation_type, server_default='following', nullable=False))
    op.create_unique_constraint('_from_user_to_user_uc', 'follow', ['from_user_id', 'to_user_id'])


def downgrade():
    op.drop_constraint('_from_user_to_user_uc', 'follow', type_='unique')
    op.drop_column('follow', 'relation')
    op.execute('DROP TYPE user_relation_type;')
