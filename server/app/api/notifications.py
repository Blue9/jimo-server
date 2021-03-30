from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.post("/token", response_model=schemas.base.SimpleResponse)
def register_token(request: schemas.user.NotificationTokenRequest,
                   firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    notifications.register_fcm_token(db, user, request.token)
    return {"success": True}


@router.delete("/token", response_model=schemas.base.SimpleResponse)
def remove_token(request: schemas.user.NotificationTokenRequest,
                 firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    notifications.remove_fcm_token(db, user, request.token)
    return {"success": True}


@router.get("/feed", response_model=schemas.notifications.NotificationFeedResponse)
def get_notification_feed(f: Optional[str] = None, l: Optional[str] = None,
                          firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """
    Returns the notification feed for the current user.
    Results can be paginated with the returned pagination token.

    Args:
        f: The last follow_id of the previous page. Can be used to get the next page of results.
        l: The last like_id of the previous page. Can be used to get the next page of results.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A NotificationFeedResponse which contains the list of notification items as well as the pagination token.
        The returned token can be used to get the next page of results.
    """
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    feed = notifications.get_notification_feed(db, user, f, l)
    if feed is None:
        raise HTTPException(404, "Failed to load more posts")
    return schemas.notifications.NotificationFeedResponse(notifications=feed, token=notifications.get_token(feed, f, l))
