import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import get_feed_store
from shared.stores.feed_store import FeedStore
from fastapi import APIRouter, Depends

from shared import schemas
from app.controllers import notifications
from app.controllers.dependencies import get_caller_user, WrappedUser
from app.db.database import get_db

router = APIRouter()


@router.post("/token", response_model=schemas.base.SimpleResponse)
async def register_token(
    request: schemas.user.NotificationTokenRequest,
    db: AsyncSession = Depends(get_db),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    await notifications.register_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.delete("/token", response_model=schemas.base.SimpleResponse)
async def remove_token(
    request: schemas.user.NotificationTokenRequest,
    db: AsyncSession = Depends(get_db),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    await notifications.remove_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.get("/feed", response_model=schemas.notifications.NotificationFeedResponse)
async def get_notification_feed(
    cursor: Optional[uuid.UUID] = None,
    feed_store: FeedStore = Depends(get_feed_store),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    """
    Returns the notification feed for the current user.
    Results can be paginated with the returned pagination token.
    """
    page_limit = 50
    user: schemas.internal.InternalUser = wrapped_user.user
    feed = await feed_store.get_notification_feed(user.id, cursor, limit=page_limit)
    next_cursor = min(item.item_id for item in feed) if len(feed) >= page_limit else None
    return schemas.notifications.NotificationFeedResponse(
        notifications=feed,
        cursor=next_cursor
    )
