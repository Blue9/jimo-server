import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import places
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.get("/{place_id}/icon", response_model=schemas.place.MapPinIcon)
def get_place_icon(place_id: uuid.UUID, firebase_user: FirebaseUser = Depends(get_firebase_user),
                   db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return places.get_place_icon(db, user, place_id)


@router.get("/{place_id}/mutualPosts", response_model=list[schemas.post.Post])
def get_mutual_posts(place_id: uuid.UUID, firebase_user: FirebaseUser = Depends(get_firebase_user),
                     db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    mutual_posts = places.get_mutual_posts(db, user, place_id, limit=100)
    if mutual_posts is None:
        raise HTTPException(404)
    return mutual_posts
