import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers import notifications

from app.api.utils import get_notification_store, get_post_store, get_user_store
from app.controllers.dependencies import get_caller_user, JimoUser
from app.db.database import get_db

from shared import schemas
from shared.stores.notification_store import NotificationStore
from shared.stores.post_store import PostStore
from shared.stores.user_store import UserStore

router = APIRouter()


@router.post("/token", response_model=schemas.base.SimpleResponse)
async def register_token(
    request: schemas.user.NotificationTokenRequest,
    db: AsyncSession = Depends(get_db),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user: schemas.internal.InternalUser = wrapped_user.user
    await notifications.register_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.delete("/token", response_model=schemas.base.SimpleResponse)
async def remove_token(
    request: schemas.user.NotificationTokenRequest,
    db: AsyncSession = Depends(get_db),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user: schemas.internal.InternalUser = wrapped_user.user
    await notifications.remove_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.get("/feed", response_model=schemas.notifications.NotificationFeedResponse)
async def get_notification_feed(
    cursor: Optional[uuid.UUID] = None,
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    notification_store: NotificationStore = Depends(get_notification_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """
    Returns the notification feed for the current user.
    Results can be paginated with the returned pagination token.
    """
    page_limit = 50
    user: schemas.internal.InternalUser = wrapped_user.user
    # TODO(gmekkat): fml
    feed = await notification_store.get_notification_feed(post_store, user.id, cursor, limit=page_limit)
    next_cursor = min(item.item_id for item in feed) if len(feed) >= page_limit else None
    return schemas.notifications.NotificationFeedResponse(notifications=feed, cursor=next_cursor)
