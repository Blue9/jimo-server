from fastapi import APIRouter, Depends

from app.features.users.entities import InternalUser
from app.features.map.map_store import MapStore
from app.features.map.types import MapResponseV3, GetMapRequest, CustomMapRequest
from app.features.users.dependencies import get_caller_user, JimoUser
from app.features.stores import get_map_store

router = APIRouter()


@router.post("/global", response_model=MapResponseV3)
async def get_global_map(
    request: GetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of all users."""
    _: InternalUser = wrapped_user.user
    pins = await map_store.get_community_map(region=request.region, categories=request.categories)
    return MapResponseV3(pins=pins)


@router.post("/following", response_model=MapResponseV3)
async def get_following_map(
    request: GetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of friends."""
    user: InternalUser = wrapped_user.user
    pins = await map_store.get_friend_map(region=request.region, user_id=user.id, categories=request.categories)
    return MapResponseV3(pins=pins)


@router.post("/saved-posts", response_model=MapResponseV3)
async def get_saved_posts_map(
    request: GetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of saved posts."""
    user: InternalUser = wrapped_user.user
    pins = await map_store.get_saved_posts_map(region=request.region, user_id=user.id, categories=request.categories)
    return MapResponseV3(pins=pins)


@router.post("/custom", response_model=MapResponseV3)
async def get_custom_map(
    request: CustomMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of the given users."""
    _: InternalUser = wrapped_user.user
    pins = await map_store.get_custom_map(region=request.region, user_ids=request.users, categories=request.categories)
    return MapResponseV3(pins=pins)
