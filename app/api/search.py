from fastapi import APIRouter, Depends

from shared import schemas

from app.api.utils import get_user_store
from app.controllers.dependencies import JimoUser, get_caller_user
from shared.stores.user_store import UserStore

router = APIRouter()


@router.get("/users", response_model=list[schemas.user.PublicUser])
async def search_users(
    q: str,
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Search for users with the given query."""
    _: schemas.internal.InternalUser = wrapped_user.user
    return await user_store.search_users(query=q)
