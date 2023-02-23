"""rename image upload columns

Revision ID: 064a2159eb7b
Revises: 804318e08ce7
Create Date: 2023-02-22 19:12:26.355218

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "064a2159eb7b"
down_revision = "804318e08ce7"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("image_upload", "firebase_blob_name", new_column_name="blob_name")
    op.alter_column("image_upload", "firebase_public_url", new_column_name="url")


def downgrade():
    op.alter_column("image_upload", "blob_name", new_column_name="firebase_blob_name")
    op.alter_column("image_upload", "url", new_column_name="firebase_public_url")
