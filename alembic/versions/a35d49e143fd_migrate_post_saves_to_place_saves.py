"""migrate post saves to place saves

Revision ID: a35d49e143fd
Revises: 2eb705cfa858
Create Date: 2023-01-22 13:41:26.018596

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a35d49e143fd"
down_revision = "2eb705cfa858"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
    insert into place_save (id, user_id, place_id, category, note, created_at)
    select
        post_save.id,
        post_save.user_id,
        post.place_id,
        post.category,
        'Want to go',
        post_save.created_at
    from post_save
    inner join post on post_save.post_id = post.id
    on conflict do nothing;
    """
    )


def downgrade():
    pass
