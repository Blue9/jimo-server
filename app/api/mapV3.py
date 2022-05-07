from fastapi import APIRouter, Depends
from shared.schemas.internal import InternalUser
from shared.schemas.map import MapResponseV3, MapLoadStrategy, CustomMapRequest, GetMapRequest
from shared.stores.place_store import PlaceStore

from app.api.utils import get_place_store
from app.controllers.dependencies import get_caller_user, JimoUser

router = APIRouter()


@router.post("/global", response_model=MapResponseV3)
async def get_global_map(
    request: GetMapRequest,
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get a map of all users."""
    user: InternalUser = wrapped_user.user
    pins = await place_store.get_map_v3(
        user.id,
        region=request.region,
        user_filter=MapLoadStrategy.everyone,
        categories=request.categories,
        limit=250
    )
    return MapResponseV3(pins=pins)


@router.post("/following", response_model=MapResponseV3)
async def get_following_map(
    request: GetMapRequest,
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get a map of all users."""
    user: InternalUser = wrapped_user.user
    pins = await place_store.get_map_v3(
        user.id,
        region=request.region,
        user_filter=MapLoadStrategy.following,
        categories=request.categories,
        limit=500
    )
    return MapResponseV3(pins=pins)


@router.post("/custom", response_model=MapResponseV3)
async def get_custom_map(
    request: CustomMapRequest,
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get a map of all users."""
    user: InternalUser = wrapped_user.user
    pins = await place_store.get_map_v3(
        user.id,
        region=request.region,
        user_filter=request.users,
        categories=request.categories,
        limit=500)
    return MapResponseV3(pins=pins)
