from typing import List

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


@router.get("/feed", response_model=List[schemas.notifications.NotificationItem])
def get_notification_feed(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    feed = notifications.get_notifications_items(db, user)
    if feed is None:
        raise HTTPException(404, "Failed to load more posts")
    return feed
