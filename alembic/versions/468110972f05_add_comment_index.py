"""add comment index

Revision ID: 468110972f05
Revises: bf5be083eeca
Create Date: 2021-05-12 21:38:44.463553

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "468110972f05"
down_revision = "bf5be083eeca"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("comment_post_id_idx", "comment", ["post_id"], unique=False)


def downgrade():
    op.drop_index("comment_post_id_idx", table_name="comment")
