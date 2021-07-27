import uuid

from firebase_admin.exceptions import FirebaseError, InvalidArgumentError
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from firebase_admin import messaging

from app import schemas
from app.models import models


def register_fcm_token(db: Session, user_id: uuid.UUID, token: str):
    existing = db.query(models.FCMToken).filter(
        and_(models.FCMToken.user_id == user_id, models.FCMToken.token == token)).count() > 0
    if existing:
        return
    fcm_token = models.FCMToken(user_id=user_id, token=token)
    db.add(fcm_token)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def remove_fcm_token(db: Session, user_id: uuid.UUID, token: str):
    db.query(models.FCMToken).filter(and_(models.FCMToken.token == token, models.FCMToken.user_id == user_id)).delete()
    db.commit()


def notify_post_liked(
    db: Session,
    post: schemas.internal.InternalPost,
    place_name: str,
    liked_by: schemas.internal.InternalUser
):
    """Notify the user their post was liked."""
    body = f"{liked_by.first_name} {liked_by.last_name} liked your post about {place_name}"
    _send_notification(db, post.user_id, body)


def notify_comment(
    db: Session,
    post: schemas.internal.InternalPost,
    place_name: str,
    comment: str,
    comment_by: schemas.internal.InternalUser
):
    body = f"{comment_by.username} commented on your post about {place_name}: \"{comment}\""
    _send_notification(db, post.user_id, body)


def notify_comment_liked(
    db: Session,
    comment: schemas.internal.InternalComment,
    liked_by: schemas.internal.InternalUser
):
    body = f"{liked_by.username} liked your comment: \"{comment.content}\""
    _send_notification(db, comment.user_id, body)


def notify_follow(db: Session, user_id: uuid.UUID, followed_by: schemas.internal.InternalUser):
    """Notify the user of their new follower."""
    body = f"{followed_by.first_name} {followed_by.last_name} started following you"
    _send_notification(db, user_id, body)


def _send_notification(db: Session, user_id: uuid.UUID, body: str):
    fcm_tokens = db.query(models.FCMToken) \
        .filter(models.FCMToken.user_id == user_id) \
        .order_by(models.FCMToken.id.desc()) \
        .limit(1) \
        .all()
    # Only notify the latest device (temporary performance improvement, remove when moving to background service)
    for fcm_token in fcm_tokens:
        message = messaging.Message(
            notification=messaging.Notification(body=body),
            apns=messaging.APNSConfig(payload=messaging.APNSPayload(messaging.Aps(sound="default"))),
            token=fcm_token.token
        )
        try:
            messaging.send(message)
        except InvalidArgumentError:
            db.delete(fcm_token)
            db.commit()
        except FirebaseError as e:
            if e.code == "NOT_FOUND":
                # Token is no longer registered
                db.delete(fcm_token)
                db.commit()
            else:
                print(f"Exception when notifying: {e}, {e.__dict__}")
        except ValueError as e:
            print(f"Exception when notifying: {e}, {e.__dict__}")
