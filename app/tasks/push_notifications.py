from asyncio import get_event_loop
from typing import Optional

import sqlalchemy as sa
from firebase_admin import messaging  # type: ignore
from firebase_admin.exceptions import FirebaseError, InvalidArgumentError  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import FCMTokenRow, UserRelationRow, UserPrefsRow
from app.core.types import UserId
from app.features.comments.entities import InternalComment
from app.features.posts.entities import InternalPost
from app.features.users.entities import InternalUser


async def notify_post_created(
    db: AsyncSession,
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
    query = sa.select(FCMTokenRow.token).where(FCMTokenRow.user_id.in_(followed_user_ids_subquery))
    result = await db.execute(query)
    # TODO: should we paginate this?
    tokens: list[str] = result.scalars().all()
    notification_body = f"{post_author.username_lower} just posted {post.place.name}"
    for token in tokens:
        await _actually_send_notification(
            fcm_token=token,
            body=notification_body,
            badge=None,
            post_id=str(post.id),
        )


async def notify_post_liked(
    db: AsyncSession,
    post: InternalPost,
    place_name: str,
    liked_by: InternalUser,
):
    """Notify the user their post was liked."""
    body = f"{liked_by.username} likes your post about {place_name}"
    await _send_notification(db, post.user_id, body, post_id=str(post.id))


async def notify_post_saved(
    db: AsyncSession,
    post: InternalPost,
    place_name: str,
    saved_by: InternalUser,
):
    """Notify the user their post was saved."""
    body = f"{saved_by.username} saved your post about {place_name}"
    await _send_notification(db, post.user_id, body, post_id=str(post.id))


async def notify_comment(
    db: AsyncSession,
    post: InternalPost,
    place_name: str,
    comment: str,
    comment_by: InternalUser,
):
    body = f'{comment_by.username} commented on your post about {place_name}: "{comment}"'
    await _send_notification(db, post.user_id, body, post_id=str(post.id))


async def notify_comment_liked(
    db: AsyncSession,
    comment: InternalComment,
    liked_by: InternalUser,
):
    body = f'{liked_by.username} likes your comment: "{comment.content}"'
    await _send_notification(db, comment.user_id, body, badge=None, post_id=str(comment.post_id))


async def notify_follow(db: AsyncSession, user_id: UserId, followed_by: InternalUser):
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
    sound = None if badge is None else "default"
    payload = messaging.APNSPayload(messaging.Aps(sound=sound, badge=badge, custom_data=custom_data), **custom_data)
    return messaging.APNSConfig(payload=payload)
