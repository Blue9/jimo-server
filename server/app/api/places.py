from typing import Optional

from fastapi import APIRouter, Header, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import places
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.get("/map", response_model=list[schemas.post.Post])
def get_map(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> list[schemas.post.Post]:
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    utils.validate_user(user)
    return places.get_map(db, user)
