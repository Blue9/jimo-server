from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import users
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db

router = APIRouter()


@router.get("/users", response_model=List[schemas.user.PublicUser])
def search_users(q: str, firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Search for users with the given query."""
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return users.search_users(db, caller_user=user, query=q)
