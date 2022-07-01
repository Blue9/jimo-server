"""add comment prefs

Revision ID: d556a5d2d28e
Revises: 468110972f05
Create Date: 2021-06-04 13:21:52.102986

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d556a5d2d28e"
down_revision = "468110972f05"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "preferences", sa.Column("comment_notifications", sa.Boolean(), server_default=sa.text("true"), nullable=False)
    )
    op.add_column(
        "preferences",
        sa.Column("comment_liked_notifications", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.drop_column("preferences", "post_notifications")


def downgrade():
    op.add_column(
        "preferences", sa.Column("post_notifications", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.drop_column("preferences", "comment_liked_notifications")
    op.drop_column("preferences", "comment_notifications")
