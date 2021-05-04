import uuid
from typing import Optional

from firebase_admin.exceptions import FirebaseError, InvalidArgumentError
from sqlalchemy import and_, exists, false
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased, Session

from firebase_admin import messaging

from app.models import models
from app.schemas.notifications import NotificationItem, ItemType
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
        except InvalidArgumentError:
            db.delete(fcm_token)
            db.commit()
        except (FirebaseError, ValueError) as e:
            print("Exception when notifying post liked", e)


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
        except InvalidArgumentError:
            db.delete(fcm_token)
            db.commit()
        except (FirebaseError, ValueError) as e:
            print("Exception when notifying new follower", e)


def get_notification_feed(
    db: Session,
    user: models.User,
    cursor: Optional[uuid.UUID] = None,
    limit: int = 50
) -> list[NotificationItem]:
    follow_query = db.query(models.UserRelation, models.User).filter(
        models.UserRelation.to_user_id == user.id,
        models.User.id == models.UserRelation.from_user_id,
        models.UserRelation.relation == models.UserRelationType.following,
        models.User.deleted == false())
    if cursor is not None:
        follow_query = follow_query.filter(models.UserRelation.id < cursor)

    post_like_alias = aliased(models.PostLike)
    like_query = db.query(
        models.PostLike,
        models.Post,
        models.User,
        exists().where(and_(post_like_alias.post_id == models.Post.id,
                            post_like_alias.user_id == user.id)).label("post_liked")
    ).filter(
        models.PostLike.post_id == models.Post.id,
        models.Post.user == user,
        models.Post.deleted == false(),
        models.User.id == models.PostLike.user_id,
        models.User.id != user.id,
        models.User.deleted == false()
    )
    if cursor is not None:
        like_query = like_query.filter(models.PostLike.id < cursor)

    follow_results = follow_query.order_by(models.UserRelation.id.desc()).limit(limit).all()
    like_results = like_query.order_by(models.PostLike.id.desc()).limit(limit).all()

    follow_items = []
    like_items = []

    for f in follow_results:
        follow_items.append(NotificationItem(type=ItemType.follow, created_at=f.UserRelation.created_at,
                                             user=f.User, item_id=f.UserRelation.id))
    for like in like_results:
        fields = ORMPost.from_orm(like.Post).dict()
        like_items.append(NotificationItem(type=ItemType.like, created_at=like.PostLike.created_at,
                                           user=like.User, item_id=like.PostLike.id,
                                           post=Post(**fields, liked=like.post_liked)))
    return sorted(follow_items + like_items, key=lambda i: i.item_id, reverse=True)[:limit]


def get_token(feed: list[NotificationItem], page_size: int) -> Optional[uuid.UUID]:
    if len(feed) < page_size:
        return None
    return min(item.item_id for item in feed)
