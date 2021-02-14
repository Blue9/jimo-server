from firebase_admin.exceptions import FirebaseError
from sqlalchemy import and_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session

from firebase_admin import messaging

from app.models.models import User, FCMToken, Post


def register_fcm_token(db: Session, user: User, token: str):
    existing = db.query(FCMToken).filter(and_(FCMToken.user_id == user.id, FCMToken.token == token)).count() > 0
    if existing:
        return
    fcm_token = FCMToken(user_id=user.id, token=token)
    db.add(fcm_token)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        print("Already registered token")
    except SQLAlchemyError:
        db.rollback()
        raise ValueError("Failed to register token")


def remove_fcm_token(db: Session, user: User, token: str):
    db.query(FCMToken).filter(and_(FCMToken.token == token, FCMToken.user_id == user.id)).delete()
    db.commit()


def notify_post_liked_if_enabled(db: Session, post: Post, liked_by: User):
    """Notify the user their post was liked if their preferences allow for it."""
    if not post.user.preferences.post_liked_notifications:
        return
    fcm_tokens = db.query(FCMToken).filter(FCMToken.user_id == post.user_id).all()
    # Notify every device the user is signed in on
    for fcm_token in fcm_tokens:
        body = f"{liked_by.first_name} {liked_by.last_name} liked your post about {post.place.name}"
        message = messaging.Message(notification=messaging.Notification(body=body), token=fcm_token.token)
        try:
            messaging.send(message)
            print("Sent message")
        except (FirebaseError, ValueError) as e:
            print(e)


def notify_follow_if_enabled(db: Session, user: User, followed_by: User):
    """Notify the user of their new follower if their preferences allow for it."""
    if not user.preferences.follow_notifications:
        return
    fcm_tokens = db.query(FCMToken).filter(FCMToken.user_id == user.id).all()
    # Notify every device the user is signed in on
    for fcm_token in fcm_tokens:
        body = f"{followed_by.first_name} {followed_by.last_name} started following you"
        message = messaging.Message(notification=messaging.Notification(body=body), token=fcm_token.token)
        try:
            messaging.send(message)
            print("Sent message")
        except (FirebaseError, ValueError) as e:
            print(e)
