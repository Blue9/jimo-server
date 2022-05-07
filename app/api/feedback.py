from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError

from shared import schemas
from app.controllers.dependencies import JimoUser, get_caller_user
from app.db.database import get_db
from shared.models import models

router = APIRouter()


@router.post("", response_model=schemas.base.SimpleResponse)
async def submit_feedback(
    request: schemas.feedback.FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    feedback = models.Feedback(user_id=user.id, contents=request.contents, follow_up=request.follow_up)
    try:
        db.add(feedback)
        await db.commit()
        return {"success": True}
    except SQLAlchemyError:
        await db.rollback()
        return {"success": False}
