from fastapi import APIRouter, Depends
from shared.api.internal import InternalUser
from shared.models.models import FeedbackRow
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.types.common import SimpleResponse
from app.api.types.feedback import FeedbackRequest
from app.controllers.dependencies import JimoUser, get_caller_user
from app.db.database import get_db

router = APIRouter()


@router.post("", response_model=SimpleResponse)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user: InternalUser = wrapped_user.user
    feedback = FeedbackRow(user_id=user.id, contents=request.contents, follow_up=request.follow_up)
    try:
        db.add(feedback)
        await db.commit()
        return {"success": True}
    except SQLAlchemyError:
        await db.rollback()
        return {"success": False}
