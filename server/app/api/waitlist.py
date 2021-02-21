from typing import Optional

from fastapi import APIRouter, Header, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import users
from app.db.database import get_db

router = APIRouter()


@router.get("/status", response_model=schemas.invite.UserWaitlistStatus)
def get_waitlist_status(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    uid = utils.get_uid_or_raise(authorization)
    return schemas.invite.UserWaitlistStatus(invited=users.is_invited(db, uid), waitlisted=users.on_waitlist(db, uid))


@router.post("/", response_model=schemas.invite.UserWaitlistStatus)
def join_waitlist(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    uid = utils.get_uid_or_raise(authorization)
    try:
        users.join_waitlist(db, uid=uid)
        return schemas.invite.UserWaitlistStatus(invited=users.is_invited(db, uid),
                                                 waitlisted=users.on_waitlist(db, uid))
    except ValueError as e:
        raise HTTPException(403, detail=str(e))


@router.post("/invites", response_model=schemas.invite.UserInviteStatus)
def invite_user(request: schemas.invite.InviteUserRequest, authorization: Optional[str] = Header(None),
                db: Session = Depends(get_db)):
    user = utils.get_user_from_auth_or_raise(db, authorization)
    return users.invite_user(db, user, request.phone_number)
