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


def notify_post_liked(db: Session, post: models.Post, liked_by: schemas.internal.InternalUser):
    """Notify the user their post was liked."""
    if not post.user.preferences.post_liked_notifications:
        return
    fcm_tokens = db.query(models.FCMToken).filter(models.FCMToken.user_id == post.user_id).all()
    # Notify every device the user is signed in on
    for fcm_token in fcm_tokens:
        body = f"{liked_by.first_name} {liked_by.last_name} liked your post about {post.place.name}"
        message = messaging.Message(notification=messaging.Notification(body=body), token=fcm_token.token)
        try:
            messaging.send(message)
        except InvalidArgumentError:
            db.delete(fcm_token)
            db.commit()
        except (FirebaseError, ValueError) as e:
            print("Exception when notifying post liked", e)


def notify_follow(db: Session, user_id: uuid.UUID, followed_by: schemas.internal.InternalUser):
    """Notify the user of their new follower."""
    fcm_tokens = db.query(models.FCMToken).filter(models.FCMToken.user_id == user_id).all()
    # Notify every device the user is signed in on
    for fcm_token in fcm_tokens:
        body = f"{followed_by.first_name} {followed_by.last_name} started following you"
        message = messaging.Message(notification=messaging.Notification(body=body), token=fcm_token.token)
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
                print(f"Exception when notifying new follower {e.__dict__}")
        except ValueError as e:
            print(f"Exception when notifying new follower {e.__dict__}")
