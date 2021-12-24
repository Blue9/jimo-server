from app.api.utils import get_user_store
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends

from shared import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user

router = APIRouter()


@router.get("/users", response_model=list[schemas.user.PublicUser])
async def search_users(
    q: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Search for users with the given query."""
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return await user_store.search_users(caller_user_id=user.id, query=q)
