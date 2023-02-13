"""convert index to constraint

Revision ID: 9c81d4344132
Revises: e35650038a94
Create Date: 2023-02-12 20:12:25.262535

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "9c81d4344132"
down_revision = "e35650038a94"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("_posts_user_place_uc", table_name="post")
    op.create_unique_constraint("_posts_user_place_uc", "post", ["user_id", "place_id"])


def downgrade():
    op.drop_constraint("_posts_user_place_uc", "post", type_="unique")
    op.create_index("_posts_user_place_uc", "post", ["user_id", "place_id"], unique=False)
