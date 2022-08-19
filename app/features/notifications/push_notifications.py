import uuid
from asyncio import get_event_loop
from typing import Optional

import sqlalchemy as sa
from firebase_admin import messaging  # type: ignore
from firebase_admin.exceptions import FirebaseError, InvalidArgumentError  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import FCMTokenRow
from app.features.comments.entities import InternalComment
from app.features.posts.entities import InternalPost
from app.features.users.entities import InternalUser


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


async def notify_follow(db: AsyncSession, user_id: uuid.UUID, followed_by: InternalUser):
    """Notify the user of their new follower."""
    body = f"{followed_by.username} started following you"
    await _send_notification(db, user_id, body, username=str(followed_by.username))


async def _send_notification(db: AsyncSession, user_id: uuid.UUID, body: str, badge: Optional[int] = 1, **kwargs):
    loop = get_event_loop()
    query = sa.select(FCMTokenRow).where(FCMTokenRow.user_id == user_id).order_by(FCMTokenRow.id.desc()).limit(1)
    fcm_tokens = (await db.execute(query)).scalars().all()
    for fcm_token in fcm_tokens:
        await db.refresh(fcm_token)
        payload = messaging.APNSPayload(messaging.Aps(sound="default", badge=badge), **kwargs)
        message = messaging.Message(
            notification=messaging.Notification(body=body),
            apns=messaging.APNSConfig(payload=payload),
            token=fcm_token.token,
        )
        try:
            await loop.run_in_executor(None, messaging.send, message)
        except InvalidArgumentError:
            await db.delete(fcm_token)
            await db.commit()
        except FirebaseError as e:
            if e.code == "NOT_FOUND":
                # Token is no longer registered
                await db.delete(fcm_token)
                await db.commit()
            else:
                print(f"Exception when notifying: {e}, {e.__dict__}")
        except ValueError as e:
            print(f"Exception when notifying: {e}, {e.__dict__}")
