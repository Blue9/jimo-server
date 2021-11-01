import uuid

from sqlalchemy import select, exists, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.models import models


def register_fcm_token(db: Session, user_id: uuid.UUID, token: str):
    query = select(models.FCMToken).where(models.FCMToken.user_id == user_id, models.FCMToken.token == token)
    existing = db.execute(exists(query).select()).scalar()
    if existing:
        return
    fcm_token = models.FCMToken(user_id=user_id, token=token)
    db.add(fcm_token)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def remove_fcm_token(db: Session, user_id: uuid.UUID, token: str):
    query = delete(models.FCMToken).where(models.FCMToken.token == token, models.FCMToken.user_id == user_id)
    db.execute(query)
    db.commit()
