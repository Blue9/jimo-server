import uuid
from typing import Optional

from sqlalchemy import false
from sqlalchemy.orm import Session

from app.models import models


def get_image_with_lock_else_throw(db: Session, user: models.User, external_id: uuid.UUID) -> models.ImageUpload:
    """Note: This locks the image row. Make sure to unlock by calling db.commit()/db.rollback()."""
    image = maybe_get_image_with_lock(db, user, external_id)
    if image is None:
        raise ValueError("Invalid image")
    return image


def maybe_get_image_with_lock(db: Session, user: models.User, external_id: uuid.UUID) -> Optional[models.ImageUpload]:
    """Note: This locks the image row. Make sure to unlock by calling db.commit()/db.rollback()."""
    return db.query(models.ImageUpload).filter(models.ImageUpload.user_id == user.id,
                                               models.ImageUpload.external_id == external_id,
                                               models.ImageUpload.firebase_public_url.isnot(None),
                                               models.ImageUpload.used == false()).with_for_update().first()
