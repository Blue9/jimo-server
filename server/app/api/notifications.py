from typing import Optional

from fastapi import APIRouter, Header, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import notifications
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.post("/token", response_model=schemas.base.SimpleResponse)
def register_token(request: schemas.user.NotificationTokenRequest, authorization: Optional[str] = Header(None),
                   db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    notifications.register_fcm_token(db, user, request.token)
    return {"success": True}


@router.delete("/token", response_model=schemas.base.SimpleResponse)
def remove_token(request: schemas.user.NotificationTokenRequest, authorization: Optional[str] = Header(None),
                 db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    notifications.remove_fcm_token(db, user, request.token)
    return {"success": True}
