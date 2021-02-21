from typing import Optional

import pydantic
from fastapi import APIRouter, Header, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import places
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.get("/map", response_model=list[schemas.post.Post])
def get_map(center_lat: float, center_long: float, span_lat: float, span_long: float,
            authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> list[schemas.post.Post]:
    try:
        bounding_box = schemas.place.RectangularRegion(center_lat=center_lat, center_long=center_long,
                                                       span_lat=span_lat, span_long=span_long)
    except pydantic.ValidationError:
        raise HTTPException(400, detail="Invalid parameters")
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    utils.validate_user(user)
    map_view: list[models.Post] = places.get_map(db, user, bounding_box)
    posts = []
    for post in map_view:
        fields = schemas.post.ORMPost.from_orm(post).dict()
        posts.append(schemas.post.Post(**fields, liked=user in post.likes))
    return posts
