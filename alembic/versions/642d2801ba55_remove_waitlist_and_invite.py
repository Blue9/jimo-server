"""remove waitlist and invite

Revision ID: 642d2801ba55
Revises: 5e67fabc1bc9
Create Date: 2023-01-03 16:35:18.049232

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "642d2801ba55"
down_revision = "5e67fabc1bc9"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("invite")
    op.drop_table("waitlist")
    op.drop_constraint("place_verified_place_data_fkey", "place", type_="foreignkey")
    op.drop_column("place", "verified_place_data")
    # ### end Alembic commands ###


def downgrade():
    pass
