"""add post notifications

Revision ID: 5e67fabc1bc9
Revises: 36824243c5a2
Create Date: 2022-08-25 01:33:29.403957

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5e67fabc1bc9"
down_revision = "36824243c5a2"
branch_labels = None
depends_on = None


delete_fcm_tokens_query = """
delete
from fcm_token
where id not in (
    select distinct on (user_id) id
    from fcm_token
    order by user_id, id desc
)
"""


def upgrade():
    op.add_column(
        "preferences", sa.Column("post_notifications", sa.Boolean(), server_default=sa.text("true"), nullable=False)
    )
    op.execute(delete_fcm_tokens_query)


def downgrade():
    op.drop_column("preferences", "post_notifications")
