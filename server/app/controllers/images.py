import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import models


def get_image_with_lock_else_throw(db: Session, user_id: uuid.UUID, image_id: uuid.UUID) -> models.ImageUpload:
    """Note: This locks the image row. Make sure to unlock by calling db.commit()/db.rollback()."""
    image = maybe_get_image_with_lock(db, user_id, image_id)
    if image is None:
        raise ValueError("Invalid image")
    return image


def maybe_get_image_with_lock(db: Session, user_id: uuid.UUID, image_id: uuid.UUID) -> Optional[models.ImageUpload]:
    """
    Note: This locks the image row. Make sure to unlock by calling db.commit()/db.rollback().

    More info on "for update" at: https://www.postgresql.org/docs/current/sql-select.html

    Relevant: "[R]ows that satisfied the query conditions as of the query snapshot will be locked, although they will
    not be returned if they were updated after the snapshot and no longer satisfy the query conditions."

    This means that if this function returns a row, used will be false and remain false until we change it or release
    the lock.
    """
    query = select(models.ImageUpload).where(models.ImageUpload.user_id == user_id,
                                             models.ImageUpload.id == image_id,
                                             models.ImageUpload.firebase_public_url.isnot(None),
                                             ~models.ImageUpload.used).with_for_update()
    return db.execute(query).scalars().first()
