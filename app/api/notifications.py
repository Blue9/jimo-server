import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from shared.api.internal import InternalUser
from shared.stores.notification_store import NotificationStore
from shared.stores.post_store import PostStore
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.types.common import SimpleResponse
from app.api.types.notifications import NotificationTokenRequest, NotificationFeedResponse
from app.api.utils import get_notification_store, get_post_store
from app.controllers import notifications
from app.controllers.dependencies import get_caller_user, JimoUser
from app.db.database import get_db

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
