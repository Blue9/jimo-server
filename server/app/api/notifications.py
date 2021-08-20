import uuid
from typing import Optional

from app.api.utils import get_user_store, get_feed_store
from stores.feed_store import FeedStore
from stores.user_store import UserStore
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import schemas
from app.api import utils
from app.controllers import notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db

router = APIRouter()


@router.post("/token", response_model=schemas.base.SimpleResponse)
def register_token(
    request: schemas.user.NotificationTokenRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(get_user_store)
):
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    notifications.register_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.delete("/token", response_model=schemas.base.SimpleResponse)
def remove_token(
    request: schemas.user.NotificationTokenRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(get_user_store)
):
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    notifications.remove_fcm_token(db, user.id, request.token)
    return {"success": True}


@router.get("/feed", response_model=schemas.notifications.NotificationFeedResponse)
def get_notification_feed(
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
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    feed = feed_store.get_notification_feed(user.id, cursor, limit=page_limit)
    next_cursor = min(item.item_id for item in feed) if len(feed) >= page_limit else None
    return schemas.notifications.NotificationFeedResponse(
        notifications=feed,
        cursor=next_cursor
    )
