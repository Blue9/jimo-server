from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import get_user_store
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError

from shared import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from shared.models import models

router = APIRouter()


@router.post("", response_model=schemas.base.SimpleResponse)
async def submit_feedback(
    request: schemas.feedback.FeedbackRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store)
):
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, uid=firebase_user.uid)
    feedback = models.Feedback(user_id=user.id, contents=request.contents, follow_up=request.follow_up)
    try:
        db.add(feedback)
        await db.commit()
        return {"success": True}
    except SQLAlchemyError:
        await db.rollback()
        return {"success": False}
