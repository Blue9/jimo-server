from app.api.utils import get_user_store
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends

from shared import schemas
from app.controllers.dependencies import JimoUser, get_caller_user

router = APIRouter()


@router.get("/users", response_model=list[schemas.user.PublicUser])
async def search_users(
    q: str,
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Search for users with the given query."""
    user: schemas.internal.InternalUser = wrapped_user.user
    return await user_store.search_users(caller_user_id=user.id, query=q)
