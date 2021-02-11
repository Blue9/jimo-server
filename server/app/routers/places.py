from typing import Optional

import pydantic
from fastapi import APIRouter, Header, Depends, HTTPException
from sqlalchemy.orm import Session

from app.controllers import users
from app.database import get_db
from app.models import models, schemas
from app.models.models import Post
from app.models.request_schemas import RectangularRegion
from app.routers import utils

router = APIRouter()


@router.get("/map", response_model=list[schemas.Post])
def get_map(center_lat: float, center_long: float, span_lat: float, span_long: float,
            authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> list[schemas.Post]:
    try:
        bounding_box = RectangularRegion(center_lat=center_lat, center_long=center_long, span_lat=span_lat,
                                         span_long=span_long)
    except pydantic.ValidationError:
        raise HTTPException(400, detail="Invalid parameters")
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    utils.validate_user(user)
    map_view: list[Post] = users.get_map(db, user, bounding_box)
    posts = []
    for post in map_view:
        fields = schemas.ORMPost.from_orm(post).dict()
        posts.append(schemas.Post(**fields, liked=user in post.likes))
    return posts
