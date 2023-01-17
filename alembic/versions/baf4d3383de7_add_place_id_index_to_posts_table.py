"""add place_id index to posts table

Revision ID: baf4d3383de7
Revises: 642d2801ba55
Create Date: 2023-01-16 19:00:22.486795

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "baf4d3383de7"
down_revision = "642d2801ba55"
branch_labels = None
depends_on = None


def upgrade():
    # For some reason, without this index, getting the map filtered to me, saved, or custom
    # times out. I think the extra constraint might completely change how postgres plans the
    # query and it might end up doing some excessive seq scanning.
    op.create_index("idx_post_place_id", "post", ["place_id"], unique=False)


def downgrade():
    op.drop_index("idx_post_place_id", table_name="post")
