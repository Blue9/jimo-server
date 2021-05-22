from app.stores.user_store import UserStore
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.post("", response_model=schemas.base.SimpleResponse)
def submit_feedback(
    request: schemas.feedback.FeedbackRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore)
):
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, uid=firebase_user.uid)
    feedback = models.Feedback(user_id=user.id, contents=request.contents, follow_up=request.follow_up)
    try:
        db.add(feedback)
        db.commit()
        return {"success": True}
    except SQLAlchemyError:
        db.rollback()
        return {"success": False}
