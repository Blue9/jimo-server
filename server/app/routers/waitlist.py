from typing import Optional

from fastapi import APIRouter, Header, Depends, HTTPException
from sqlalchemy.orm import Session

from app.controllers import users
from app.database import get_db
from app.models.request_schemas import InviteUserRequest
from app.models.response_schemas import UserWaitlistStatus, UserInviteStatus
from app.routers import utils
from app.routers.utils import get_uid_or_raise

router = APIRouter()


@router.get("/status", response_model=UserWaitlistStatus)
def get_waitlist_status(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    uid = get_uid_or_raise(authorization)
    return UserWaitlistStatus(invited=users.is_invited(db, uid), waitlisted=users.on_waitlist(db, uid))


@router.post("/", response_model=UserWaitlistStatus)
def join_waitlist(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    uid = get_uid_or_raise(authorization)
    try:
        users.join_waitlist(db, uid=uid)
        return UserWaitlistStatus(invited=users.is_invited(db, uid), waitlisted=users.on_waitlist(db, uid))
    except ValueError as e:
        raise HTTPException(403, detail=str(e))


@router.post("/invites", response_model=UserInviteStatus)
def invite_user(request: InviteUserRequest, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    user = utils.get_user_from_auth_or_raise(db, authorization)
    return users.invite_user(db, user, request.phone_number)
