import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from shared.api.internal import InternalUser
from shared.stores.notification_store import NotificationStore
from shared.stores.post_store import PostStore
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.common import SimpleResponse
from app.core.database import get_db
from app.features.notifications import notifications
from app.features.notifications.types import NotificationTokenRequest, NotificationFeedResponse
from app.features.users.dependencies import JimoUser, get_caller_user
from app.features.utils import get_post_store, get_notification_store

router = APIRouter()


@router.post("/token", response_model=SimpleResponse)
async def register_token(
    request: NotificationTokenRequest,
    db: AsyncSession = Depends(get_db),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user: InternalUser = wrapped_user.user
    await notifications.register_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.delete("/token", response_model=SimpleResponse)
async def remove_token(
    request: NotificationTokenRequest,
    db: AsyncSession = Depends(get_db),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user: InternalUser = wrapped_user.user
    await notifications.remove_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.get("/feed", response_model=NotificationFeedResponse)
async def get_notification_feed(
    cursor: Optional[uuid.UUID] = None,
    post_store: PostStore = Depends(get_post_store),
    notification_store: NotificationStore = Depends(get_notification_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """
    Returns the notification feed for the current user.
    Results can be paginated with the returned pagination token.
    """
    page_limit = 50
    user: InternalUser = wrapped_user.user
    feed, next_cursor = await notification_store.get_notification_feed(post_store, user.id, cursor, limit=page_limit)
    return NotificationFeedResponse(notifications=feed, cursor=next_cursor)
