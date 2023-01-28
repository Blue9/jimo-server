"""populate city and category

Revision ID: 812e3bffe118
Revises: 998dcad465fd
Create Date: 2023-01-28 18:20:38.608021

"""
from alembic import op

from app.tasks.place_metadata import UPDATE_FOR_ALL_PLACES_QUERY


# revision identifiers, used by Alembic.
revision = "812e3bffe118"
down_revision = "998dcad465fd"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(UPDATE_FOR_ALL_PLACES_QUERY)


def downgrade():
    pass
