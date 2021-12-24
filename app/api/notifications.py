import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import get_user_store, get_feed_store
from shared.stores.feed_store import FeedStore
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends

from shared import schemas
from app.api import utils
from app.controllers import notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db

router = APIRouter()


@router.post("/token", response_model=schemas.base.SimpleResponse)
async def register_token(
    request: schemas.user.NotificationTokenRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store)
):
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    await notifications.register_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.delete("/token", response_model=schemas.base.SimpleResponse)
async def remove_token(
    request: schemas.user.NotificationTokenRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store)
):
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    await notifications.remove_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.get("/feed", response_model=schemas.notifications.NotificationFeedResponse)
async def get_notification_feed(
    cursor: Optional[uuid.UUID] = None,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    feed_store: FeedStore = Depends(get_feed_store)
):
    """
    Returns the notification feed for the current user.
    Results can be paginated with the returned pagination token.
    """
    page_limit = 50
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    feed = await feed_store.get_notification_feed(user.id, cursor, limit=page_limit)
    next_cursor = min(item.item_id for item in feed) if len(feed) >= page_limit else None
    return schemas.notifications.NotificationFeedResponse(
        notifications=feed,
        cursor=next_cursor
    )
