"""add nightlife category

Revision ID: 7861816ef9bb
Revises: 057f1e5e7a15
Create Date: 2021-11-02 22:55:37.391612

"""
from alembic import op

# revision identifiers, used by Alembic.
from shared.models.models import CategoryRow
from sqlalchemy import delete
from sqlalchemy.orm import Session

revision = "7861816ef9bb"
down_revision = "057f1e5e7a15"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    nightlife = CategoryRow(name="nightlife")
    session.add(nightlife)
    session.commit()


def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)
    query = delete(CategoryRow).where(CategoryRow.name == "nightlife")
    session.execute(query)
    session.commit()
