from asyncio import get_event_loop
from typing import Optional

import sqlalchemy as sa
from app.core.database.engine import get_db_context
from app.features.users.user_store import UserStore
from firebase_admin import messaging  # type: ignore
from firebase_admin.exceptions import FirebaseError, InvalidArgumentError  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import FCMTokenRow, UserRelationRow, UserPrefsRow
from app.core.types import UserId
from app.features.comments.entities import InternalComment
from app.features.posts.entities import InternalPost
from app.features.users.entities import InternalUser


async def notify_post_created(
    post: InternalPost,
    post_author: InternalUser,
):
    """Notify the post author's followers that they made a new post."""
    if post_author.is_featured:
        # Don't notify when a featured account posts because we go on posting sprees and don't want to annoy our users
        return
    followed_user_ids_subquery = (
        sa.select(UserRelationRow.from_user_id)
        .join(UserPrefsRow, UserRelationRow.from_user_id == UserPrefsRow.user_id)
        .where(UserRelationRow.to_user_id == post_author.id, UserPrefsRow.post_notifications)
    )
    query = sa.select(FCMTokenRow).where(FCMTokenRow.user_id.in_(followed_user_ids_subquery))
    async with get_db_context() as db:
        result = await db.execute(query)
        # TODO: should we paginate this?
        tokens = result.scalars().all()
        fcm_tokens: list[str] = [token.token for token in tokens]
    notification_body = f"{post_author.username_lower} just posted {post.place.name}"
    for token in fcm_tokens:
        await _actually_send_notification(
            fcm_token=token,
            body=notification_body,
            badge=None,
            post_id=str(post.id),
        )


async def notify_post_liked(post: InternalPost, liked_by: InternalUser):
    """Notify the user their post was liked if their notifications are enabled."""
    async with get_db_context() as db:
        user_store = UserStore(db=db)
        author_prefs = await user_store.get_user_preferences(post.user_id)
        if liked_by.id != post.user_id and author_prefs.post_liked_notifications:
            body = f"{liked_by.username} likes your post about {post.place.name}"
            await _send_notification(db, post.user_id, body, post_id=str(post.id))


async def notify_comment(
    post: InternalPost,
    comment: InternalComment,
    comment_by: InternalUser,
):
    async with get_db_context() as db:
        user_store = UserStore(db=db)
        post_author_prefs = await user_store.get_user_preferences(post.user_id)
        if comment_by.id != post.user_id and post_author_prefs.comment_notifications:
            body = f'{comment_by.username} commented on your post about {post.place.name}: "{comment.content}"'
            await _send_notification(db, post.user_id, body, post_id=str(post.id))


async def notify_comment_liked(
    comment: InternalComment,
    liked_by: InternalUser,
):
    if liked_by.id == comment.user_id:
        # Don't notify the user who created the comment
        return
    async with get_db_context() as db:
        commenter_prefs = await UserStore(db=db).get_user_preferences(comment.user_id)
        if commenter_prefs.comment_liked_notifications:
            body = f'{liked_by.username} likes your comment: "{comment.content}"'
            await _send_notification(db, comment.user_id, body, badge=None, post_id=str(comment.post_id))


async def notify_many_followed(user: InternalUser, followed_users: list[UserId]):
    """Note: This makes N queries, can optimize later"""
    async with get_db_context() as db:
        user_store = UserStore(db)
        for followed in followed_users:
            prefs = await user_store.get_user_preferences(followed)
            if prefs.follow_notifications:
                await _actually_notify_follow(db, followed, followed_by=user)


async def notify_follow(user_id: UserId, followed_by: InternalUser):
    async with get_db_context() as db:
        prefs = await UserStore(db).get_user_preferences(user_id)
        if prefs.follow_notifications:
            await _actually_notify_follow(db, user_id, followed_by)


async def _actually_notify_follow(db: AsyncSession, user_id: UserId, followed_by: InternalUser):
    """Notify the user of their new follower."""
    body = f"{followed_by.username} started following you"
    await _send_notification(db, user_id, body, username=str(followed_by.username))


async def _send_notification(db: AsyncSession, user_id: UserId, body: str, badge: Optional[int] = 1, **kwargs):
    query = sa.select(FCMTokenRow.token).where(FCMTokenRow.user_id == user_id).order_by(FCMTokenRow.id.desc())
    result = await db.execute(query)
    fcm_token: Optional[str] = result.scalars().first()
    if fcm_token is None:
        return
    await _actually_send_notification(fcm_token, body, badge, **kwargs)


async def _actually_send_notification(fcm_token: str, body: str, badge: Optional[int], **kwargs):
    apns = _get_apns(badge, **kwargs)
    message = messaging.Message(notification=messaging.Notification(body=body), apns=apns, token=fcm_token)
    try:
        loop = get_event_loop()
        await loop.run_in_executor(None, messaging.send, message)
    except (ValueError, FirebaseError, InvalidArgumentError) as e:
        print(f"Exception when notifying: {e}, {e.__dict__}")


def _get_apns(badge: Optional[int], **custom_data) -> messaging.APNSConfig:
    payload = messaging.APNSPayload(messaging.Aps(sound=None, badge=badge, custom_data=custom_data), **custom_data)
    return messaging.APNSConfig(payload=payload)
