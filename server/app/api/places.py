from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import places
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.get("/map", response_model=list[schemas.post.Post])
def get_map(firebase_user: FirebaseUser = Depends(get_firebase_user),
            db: Session = Depends(get_db)) -> list[schemas.post.Post]:
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    utils.validate_user(user)
    return places.get_map(db, user)
