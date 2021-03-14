from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import users
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db

router = APIRouter()


@router.get("/status", response_model=schemas.invite.UserWaitlistStatus)
def get_waitlist_status(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    return schemas.invite.UserWaitlistStatus(invited=users.is_invited(db, firebase_user),
                                             waitlisted=users.on_waitlist(db, firebase_user))


@router.post("", response_model=schemas.invite.UserWaitlistStatus)
def join_waitlist(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    try:
        users.join_waitlist(db, firebase_user)
        return schemas.invite.UserWaitlistStatus(invited=users.is_invited(db, firebase_user),
                                                 waitlisted=users.on_waitlist(db, firebase_user))
    except ValueError as e:
        raise HTTPException(403, detail=str(e))


@router.post("/invites", response_model=schemas.invite.UserInviteStatus)
def invite_user(request: schemas.invite.InviteUserRequest, firebase_user: FirebaseUser = Depends(get_firebase_user),
                db: Session = Depends(get_db)):
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return users.invite_user(db, user, request.phone_number)
