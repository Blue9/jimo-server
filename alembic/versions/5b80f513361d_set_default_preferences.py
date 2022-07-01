"""set_default_preferences

Revision ID: 5b80f513361d
Revises: d0f473550741
Create Date: 2022-06-28 21:30:41.704223

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "5b80f513361d"
down_revision = "d0f473550741"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""alter table preferences alter column follow_notifications set default true""")
    op.execute("""alter table preferences alter column post_liked_notifications set default true""")


def downgrade():
    pass
