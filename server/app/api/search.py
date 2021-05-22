from app.stores.user_store import UserStore
from fastapi import APIRouter, Depends

from app import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user

router = APIRouter()


@router.get("/users", response_model=list[schemas.user.PublicUser])
def search_users(
    q: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore)
):
    """Search for users with the given query."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return user_store.search_users(caller_user_id=user.id, query=q)
