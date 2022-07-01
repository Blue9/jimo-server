"""add indexes for aggregates

Revision ID: a18f47403d7c
Revises: e134475a36ec
Create Date: 2021-05-11 23:39:41.938469

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a18f47403d7c"
down_revision = "e134475a36ec"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("user_relation_from_user_id_relation_idx", "follow", ["from_user_id", "relation"], unique=False)
    op.create_index("user_relation_to_user_id_relation_idx", "follow", ["to_user_id", "relation"], unique=False)
    op.create_index("post_like_post_id_idx", "post_like", ["post_id"], unique=False)


def downgrade():
    op.drop_index("post_like_post_id_idx", table_name="post_like")
    op.drop_index("user_relation_to_user_id_relation_idx", table_name="follow")
    op.drop_index("user_relation_from_user_id_relation_idx", table_name="follow")
