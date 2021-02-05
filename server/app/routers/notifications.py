from typing import Optional

from fastapi import APIRouter, Header, Depends
from sqlalchemy.orm import Session

from app.controllers import notifications
from app.database import get_db
from app.models import models
from app.models.request_schemas import NotificationTokenRequest
from app.models.response_schemas import NotificationTokenResponse
from app.routers import utils

router = APIRouter()


@router.post("/token", response_model=NotificationTokenResponse)
def register_token(request: NotificationTokenRequest, authorization: Optional[str] = Header(None),
                   db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    try:
        notifications.register_fcm_token(db, user, request.token)
        return NotificationTokenResponse(success=True)
    except Exception as e:
        print("Exception when registering token", e)
        return NotificationTokenResponse(success=False)


@router.delete("/token", response_model=NotificationTokenResponse)
def remove_token(request: NotificationTokenRequest, authorization: Optional[str] = Header(None),
                 db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    try:
        notifications.remove_fcm_token(db, user, request.token)
        return NotificationTokenResponse(success=True)
    except Exception as e:
        print("Exception when removing token", e)
        return NotificationTokenResponse(success=False)
