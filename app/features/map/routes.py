from fastapi import APIRouter, Depends, HTTPException
from app.core.firebase import FirebaseUser, get_firebase_user

from app.features.map.map_store import MapStore
from app.features.map.types import GetMapResponse, GetMapRequest
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
        # Anonymous accounts
        if request.map_type == "custom":
            pins = await map_store.get_featured_users_map(
                region=request.region, user_ids=request.user_ids or [], categories=request.categories, limit=200
            )
            return GetMapResponse(pins=pins)
        elif request.map_type == "community":
            pins = await map_store.get_guest_community_map(
                region=request.region, categories=request.categories, limit=200
            )
            return GetMapResponse(pins=pins)
    raise HTTPException(403)
