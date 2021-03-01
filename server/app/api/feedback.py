from typing import Optional

from fastapi import APIRouter, Header, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app import schemas
from app.api import utils
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.post("/", response_model=schemas.base.SimpleResponse)
def submit_feedback(request: schemas.feedback.FeedbackRequest, authorization: Optional[str] = Header(None),
                    db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    feedback = models.Feedback(user_id=user.id, contents=request.contents, follow_up=request.follow_up)
    try:
        db.add(feedback)
        db.commit()
        return {"success": True}
    except SQLAlchemyError:
        db.rollback()
        return {"success": False}
