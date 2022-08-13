"""add saved post table

Revision ID: d0f473550741
Revises: 7861816ef9bb
Create Date: 2022-05-10 21:13:13.572272

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d0f473550741"
down_revision = "7861816ef9bb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "post_save",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["post_id"], ["post.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "post_id", name="_saved_post_user_post_uc"),
    )
    op.create_index("saved_post_user_id_idx", "post_save", ["user_id"], unique=False)


def downgrade():
    op.drop_index("saved_post_user_id_idx", table_name="post_save")
    op.drop_table("post_save")
