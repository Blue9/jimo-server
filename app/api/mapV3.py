from fastapi import APIRouter, Depends
from shared.api.internal import InternalUser
from shared.map.strategy import (
    CategoryFilter,
    EveryoneFilter,
    FriendsFilter,
    SavedPostsFilter,
    UserListFilter,
)
from shared.stores.map_store import MapStore

from app.api.types.map import MapResponseV3, CustomMapRequest, GetMapRequest
from app.api.utils import get_map_store
from app.controllers.dependencies import get_caller_user, JimoUser

router = APIRouter()


@router.post("/global", response_model=MapResponseV3)
async def get_global_map(
    request: GetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of all users."""
    _: InternalUser = wrapped_user.user
    pins = await map_store.get_map_v3(
        region=request.region,
        map_filter=EveryoneFilter(),
        category_filter=CategoryFilter(request.categories),  # type: ignore
        limit=250,
    )
    return MapResponseV3(pins=pins)


@router.post("/following", response_model=MapResponseV3)
async def get_following_map(
    request: GetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of friends."""
    user: InternalUser = wrapped_user.user
    pins = await map_store.get_map_v3(
        region=request.region,
        map_filter=FriendsFilter(user_id=user.id),
        category_filter=CategoryFilter(request.categories),  # type: ignore
        limit=500,
    )
    return MapResponseV3(pins=pins)


@router.post("/saved-posts", response_model=MapResponseV3)
async def get_saved_posts_map(
    request: GetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of saved posts."""
    user: InternalUser = wrapped_user.user
    pins = await map_store.get_map_v3(
        region=request.region,
        map_filter=SavedPostsFilter(user_id=user.id),
        category_filter=CategoryFilter(request.categories),  # type: ignore
        limit=500,
    )
    return MapResponseV3(pins=pins)


@router.post("/custom", response_model=MapResponseV3)
async def get_custom_map(
    request: CustomMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of the given users."""
    _: InternalUser = wrapped_user.user
    pins = await map_store.get_map_v3(
        region=request.region,
        map_filter=UserListFilter(user_ids=request.users),
        category_filter=CategoryFilter(request.categories),  # type: ignore
        limit=500,
    )
    return MapResponseV3(pins=pins)
