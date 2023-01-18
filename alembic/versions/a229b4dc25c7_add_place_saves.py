"""add place saves

Revision ID: a229b4dc25c7
Revises: baf4d3383de7
Create Date: 2023-01-18 15:00:45.258724

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a229b4dc25c7"
down_revision = "baf4d3383de7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "place_save",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("place_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["place.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "place_id", name="_place_save_user_place_uc"),
    )
    op.create_index("idx_place_save_place_id", "place_save", ["place_id"], unique=False)


def downgrade():
    op.drop_index("idx_place_save_place_id", table_name="place_save")
    op.drop_table("place_save")
