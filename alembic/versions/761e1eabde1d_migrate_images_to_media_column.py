"""migrate images to media column

Revision ID: 761e1eabde1d
Revises: 23b307c6e876
Create Date: 2023-04-18 14:55:06.077997

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "761e1eabde1d"
down_revision = "23b307c6e876"
branch_labels = None
depends_on = None

command = """
WITH updated_media AS (
  SELECT
    p.id,
    p.media,
    iu.id AS iu_id,
    iu.blob_name AS iu_blob_name,
    iu.url AS iu_url
  FROM
    post p
    JOIN image_upload iu ON p.image_id = iu.id
)
UPDATE
  post
SET
  media = CASE
    WHEN updated_media.media = '[]' THEN
      jsonb_build_array(
        jsonb_build_object(
          'id', updated_media.iu_id, 'blob_name', updated_media.iu_blob_name, 'url', updated_media.iu_url))
    ELSE
      updated_media.media
  END
FROM
  updated_media
WHERE
  post.id = updated_media.id;
"""


def upgrade():
    op.execute(command)


def downgrade():
    pass
