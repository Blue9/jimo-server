from fastapi import APIRouter, Depends, HTTPException
from app.core.firebase import FirebaseUser, get_firebase_user

from app.features.users.entities import InternalUser
from app.features.map.map_store import MapStore
from app.features.map.types import GetMapResponse, DeprecatedGetMapRequest, DeprecatedCustomMapRequest, GetMapRequest
from app.features.users.dependencies import get_caller_user
from app.features.stores import get_map_store, get_user_store
from app.features.users.user_store import UserStore

router = APIRouter()


@router.post("/load", response_model=GetMapResponse)
async def load_map(
    request: GetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
):
    """Get the map. The passed in region should be in SRID 4326."""
    user = await user_store.get_user(uid=firebase_user.uid)
    if user:
        pins = await map_store.get_map(
            user_id=user.id,
            user_icon_url=user.profile_picture_url,
            region=request.region,
            user_filter=request.map_type,
            user_ids=request.user_ids,
            categories=request.categories,
        )
        return GetMapResponse(pins=pins)
    else:
        if request.map_type != "custom":
            raise HTTPException(403)
        pins = await map_store.get_featured_users_map(
            region=request.region, user_ids=request.user_ids or [], categories=request.categories, limit=200
        )
        return GetMapResponse(pins=pins)


@router.post("/global", response_model=GetMapResponse)
async def get_global_map(
    request: DeprecatedGetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    _user: InternalUser = Depends(get_caller_user),
):
    """Get a map of all users."""
    pins = await map_store.get_community_map(region=request.region, categories=request.categories)
    return GetMapResponse(pins=pins)


@router.post("/following", response_model=GetMapResponse)
async def get_following_map(
    request: DeprecatedGetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get a map of friends."""
    pins = await map_store.get_friend_map(region=request.region, user_id=user.id, categories=request.categories)
    return GetMapResponse(pins=pins)


@router.post("/saved-posts", response_model=GetMapResponse)
async def get_saved_posts_map(
    request: DeprecatedGetMapRequest,
    map_store: MapStore = Depends(get_map_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get a map of saved posts."""
    pins = await map_store.get_saved_posts_map(region=request.region, user_id=user.id, categories=request.categories)
    return GetMapResponse(pins=pins)


@router.post("/custom", response_model=GetMapResponse)
async def get_custom_map(
    request: DeprecatedCustomMapRequest,
    map_store: MapStore = Depends(get_map_store),
    _user: InternalUser = Depends(get_caller_user),
):
    """Get a map of the given users."""
    pins = await map_store.get_custom_map(region=request.region, user_ids=request.users, categories=request.categories)
    return GetMapResponse(pins=pins)
