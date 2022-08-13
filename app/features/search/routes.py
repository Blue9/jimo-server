from fastapi import APIRouter, Depends

from app.features.users.dependencies import get_caller_user, JimoUser
from app.features.users.entities import PublicUser
from app.features.users.user_store import UserStore
from app.features.utils import get_user_store

router = APIRouter()


@router.get("/users", response_model=list[PublicUser])
async def search_users(
    q: str,
    user_store: UserStore = Depends(get_user_store),
    _wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Search for users with the given query."""
    return await user_store.search_users(query=q)
