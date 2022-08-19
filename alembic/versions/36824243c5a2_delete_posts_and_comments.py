"""delete posts and comments

Revision ID: 36824243c5a2
Revises: 5b80f513361d
Create Date: 2022-08-13 17:00:37.041593

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

from app.core.database.models import PostRow, CommentRow

# revision identifiers, used by Alembic.
revision = '36824243c5a2'
down_revision = '5b80f513361d'
branch_labels = None
depends_on = None


def upgrade():
    session = Session(bind=op.get_bind())
    session.execute(sa.delete(PostRow).where(PostRow.deleted))
    session.execute(sa.delete(CommentRow).where(CommentRow.deleted))
    session.commit()


def downgrade():
    pass
