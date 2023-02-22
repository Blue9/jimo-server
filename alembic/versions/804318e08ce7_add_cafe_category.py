"""add cafe category

Revision ID: 804318e08ce7
Revises: d1aecdbe4107
Create Date: 2023-02-22 18:32:02.940651

"""
from alembic import op
from sqlalchemy import delete
from sqlalchemy.orm import Session
from app.core.database.models import CategoryRow


# revision identifiers, used by Alembic.
revision = "804318e08ce7"
down_revision = "d1aecdbe4107"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    cafe = CategoryRow(name="cafe")
    session.add(cafe)
    session.commit()


def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    query = delete(CategoryRow).where(CategoryRow.name == "cafe")
    session.execute(query)
    session.commit()
