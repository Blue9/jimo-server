import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.engine import get_db
from app.features.notifications import tokens
from app.features.places.place_store import PlaceStore
from app.features.users.entities import InternalUser
from app.core.types import SimpleResponse
from app.features.notifications.activity_feed_store import ActivityFeedStore
from app.features.notifications.types import (
    NotificationTokenRequest,
    NotificationFeedResponse,
)
from app.features.posts.post_store import PostStore
from app.features.users.dependencies import get_caller_user
from app.features.stores import get_place_store, get_post_store, get_notification_store

router = APIRouter(tags=["notifications"])


@router.post("/token", response_model=SimpleResponse)
async def register_token(
    request: NotificationTokenRequest,
    db: AsyncSession = Depends(get_db),
    user: InternalUser = Depends(get_caller_user),
):
    """Register the Firebase Cloud Messaging token."""
    await tokens.register_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.delete("/token", response_model=SimpleResponse)
async def remove_token(
    request: NotificationTokenRequest,
    db: AsyncSession = Depends(get_db),
    user: InternalUser = Depends(get_caller_user),
):
    """De-register the Firebase Cloud Messaging token."""
    await tokens.remove_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.get("/feed", response_model=NotificationFeedResponse)
async def get_notification_feed(
    cursor: Optional[uuid.UUID] = None,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    notification_store: ActivityFeedStore = Depends(get_notification_store),
    user: InternalUser = Depends(get_caller_user),
):
    """
    Returns the notification feed for the current user.
    Results can be paginated with the returned pagination token.
    """
    page_limit = 50
    feed, next_cursor = await notification_store.get_notification_feed(
        post_store=post_store, place_store=place_store, user_id=user.id, cursor=cursor, limit=page_limit
    )
    return NotificationFeedResponse(notifications=feed, cursor=next_cursor)
