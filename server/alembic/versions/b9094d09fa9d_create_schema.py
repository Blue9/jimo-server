"""create schema

Revision ID: b9094d09fa9d
Revises:
Create Date: 2021-03-29 21:18:08.808821

"""
from alembic import op

# revision identifiers, used by Alembic.
from sqlalchemy.orm import Session

from app.controllers import categories
from app.models import models

revision = 'b9094d09fa9d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""CREATE EXTENSION IF NOT EXISTS postgis""")
    bind = op.get_bind()
    models.Base.metadata.create_all(bind=bind)
    # Add categories to db
    session = Session(bind=bind)
    categories.add_categories_to_db(session)


def downgrade():
    bind = op.get_bind()
    models.Base.metadata.drop_all(bind=bind)
    op.execute("""DROP EXTENSION IF EXISTS postgis""")
