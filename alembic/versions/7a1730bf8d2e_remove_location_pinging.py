"""remove location pinging

Revision ID: 7a1730bf8d2e
Revises: 761e1eabde1d
Create Date: 2023-05-25 22:53:38.562402

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "7a1730bf8d2e"
down_revision = "761e1eabde1d"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("location")


def downgrade():
    op.create_table(
        "location",
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("uid", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("latitude", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
        sa.Column("longitude", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            autoincrement=False,
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="location_pkey"),
    )
