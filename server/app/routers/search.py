from typing import List, Optional

from fastapi import APIRouter, Header, Depends
from sqlalchemy.orm import Session

from app.controllers import users
from app.database import get_db
from app.models import schemas
from app.routers import utils

router = APIRouter()


@router.get("/users", response_model=List[schemas.PublicUser])
def search_users(q: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Search for users with the given query."""
    _user = utils.get_user_from_auth_or_raise(db, authorization)
    return users.search_users(db, q)
