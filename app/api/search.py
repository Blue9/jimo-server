from fastapi import APIRouter, Depends
from shared.api.user import PublicUser
from shared.stores.user_store import UserStore

from app.api.utils import get_user_store
from app.controllers.dependencies import JimoUser, get_caller_user

router = APIRouter()


@router.get("/users", response_model=list[PublicUser])
async def search_users(
    q: str,
    user_store: UserStore = Depends(get_user_store),
    _wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Search for users with the given query."""
    return await user_store.search_users(query=q)
