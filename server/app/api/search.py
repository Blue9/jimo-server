from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.controllers import users
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db

router = APIRouter()


@router.get("/users", response_model=List[schemas.user.PublicUser])
def search_users(q: str, _firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Search for users with the given query."""
    return users.search_users(db, q)
