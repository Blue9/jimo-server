from fastapi import APIRouter, Depends

from app.features.users.entities import InternalUser
from app.features.map.map_store import MapStore
from app.features.map.types import GetMapResponse, DeprecatedGetMapRequest, DeprecatedCustomMapRequest, GetMapRequest
from app.features.users.dependencies import get_caller_user, JimoUser
from app.features.stores import get_map_store

router = APIRouter()


@router.post("/load", response_model=GetMapResponse)
async def load_map(
    request: GetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the map."""
    user: InternalUser = wrapped_user.user
    pins = await map_store.get_map(
        user_id=user.id,
        region=request.region,
        categories=request.categories or [],
        user_filter=request.map_type,
        user_ids=request.user_ids,
    )
    return GetMapResponse(pins=pins)


@router.post("/global", response_model=GetMapResponse)
async def get_global_map(
    request: DeprecatedGetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of all users."""
    _: InternalUser = wrapped_user.user
    pins = await map_store.get_community_map(region=request.region, categories=request.categories)
    return GetMapResponse(pins=pins)


@router.post("/following", response_model=GetMapResponse)
async def get_following_map(
    request: DeprecatedGetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of friends."""
    user: InternalUser = wrapped_user.user
    pins = await map_store.get_friend_map(region=request.region, user_id=user.id, categories=request.categories)
    return GetMapResponse(pins=pins)


@router.post("/saved-posts", response_model=GetMapResponse)
async def get_saved_posts_map(
    request: DeprecatedGetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of saved posts."""
    user: InternalUser = wrapped_user.user
    pins = await map_store.get_saved_posts_map(region=request.region, user_id=user.id, categories=request.categories)
    return GetMapResponse(pins=pins)


@router.post("/custom", response_model=GetMapResponse)
async def get_custom_map(
    request: DeprecatedCustomMapRequest,
    map_store: MapStore = Depends(get_map_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get a map of the given users."""
    _: InternalUser = wrapped_user.user
    pins = await map_store.get_custom_map(region=request.region, user_ids=request.users, categories=request.categories)
    return GetMapResponse(pins=pins)
