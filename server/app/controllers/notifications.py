from typing import Optional

from firebase_admin.exceptions import FirebaseError
from sqlalchemy import and_, false
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from firebase_admin import messaging

from app.models import models
from app.schemas.notifications import NotificationItem, PaginationToken, ItemType
from app.schemas.post import ORMPost, Post


def register_fcm_token(db: Session, user: models.User, token: str):
    existing = db.query(models.FCMToken).filter(
        and_(models.FCMToken.user_id == user.id, models.FCMToken.token == token)).count() > 0
    if existing:
        return
    fcm_token = models.FCMToken(user_id=user.id, token=token)
    db.add(fcm_token)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()


def remove_fcm_token(db: Session, user: models.User, token: str):
    db.query(models.FCMToken).filter(and_(models.FCMToken.token == token, models.FCMToken.user_id == user.id)).delete()
    db.commit()


def notify_post_liked_if_enabled(db: Session, post: models.Post, liked_by: models.User):
    """Notify the user their post was liked if their preferences allow for it."""
    if not post.user.preferences.post_liked_notifications:
        return
    fcm_tokens = db.query(models.FCMToken).filter(models.FCMToken.user_id == post.user_id).all()
    # Notify every device the user is signed in on
    for fcm_token in fcm_tokens:
        body = f"{liked_by.first_name} {liked_by.last_name} liked your post about {post.place.name}"
        message = messaging.Message(notification=messaging.Notification(body=body), token=fcm_token.token)
        try:
            messaging.send(message)
            print("Sent message")
        except (FirebaseError, ValueError) as e:
            print(e)


def notify_follow_if_enabled(db: Session, user: models.User, followed_by: models.User):
    """Notify the user of their new follower if their preferences allow for it."""
    if not user.preferences.follow_notifications:
        return
    fcm_tokens = db.query(models.FCMToken).filter(models.FCMToken.user_id == user.id).all()
    # Notify every device the user is signed in on
    for fcm_token in fcm_tokens:
        body = f"{followed_by.first_name} {followed_by.last_name} started following you"
        message = messaging.Message(notification=messaging.Notification(body=body), token=fcm_token.token)
        try:
            messaging.send(message)
            print("Sent message")
        except (FirebaseError, ValueError) as e:
            print(e)


def get_notifications_items(db: Session, user: models.User,
                            token: Optional[PaginationToken] = None) -> list[NotificationItem]:
    follow_query = db.query(models.follow, models.User).filter(
                                  models.follow.c.to_user_id == user.id,
                                  models.User.id == models.follow.c.from_user_id,
                                  models.User.deleted == false())
    if token is not None and token.follow_id is not None:
        follow_query = follow_query.filter(models.follow.c.id < token.follow_id)

    like_query = db.query(models.post_like, models.Post, models.User).filter(
            models.post_like.c.post_id == models.Post.id,
            models.Post.user == user,
            models.Post.deleted == false(),
            models.User.id == models.post_like.c.user_id,
            models.User.id != user.id,
            models.User.deleted == false())
    if token is not None and token.like_id is not None:
        like_query = like_query.filter(models.post_like.c.id < token.like_id)

    follow_results = follow_query.order_by(models.follow.c.created_at.desc()).limit(50).all()
    like_results = like_query.order_by(models.post_like.c.created_at.desc()).limit(50).all()

    follow_items = []
    like_items = []

    for f in follow_results:
        follow_items.append(NotificationItem(type=ItemType.follow, created_at=f.created_at,
                                             user=f.User, item_id=f.id))
    for like in like_results:
        fields = ORMPost.from_orm(like.Post).dict()
        like_items.append(NotificationItem(type=ItemType.like, created_at=like.created_at,
                                           user=like.User, item_id=like.id,
                                           post=Post(**fields, liked=user in like.Post.likes)))
    return sorted(follow_items + like_items, key=lambda i: i.created_at, reverse=True)[0:50]
