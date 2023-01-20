"""remove place save category

Revision ID: 553cbccae181
Revises: 345b58ae4a73
Create Date: 2023-01-20 15:48:57.722847

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "553cbccae181"
down_revision = "345b58ae4a73"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("place_save_category_fkey", "place_save", type_="foreignkey")
    op.drop_column("place_save", "category")


def downgrade():
    op.add_column("place_save", sa.Column("category", sa.TEXT(), autoincrement=False, nullable=False))
    op.create_foreign_key("place_save_category_fkey", "place_save", "category", ["category"], ["name"])
