import uuid

from app.api.utils import get_post_store, get_place_store
from shared.stores.place_store import PlaceStore
from shared.stores.post_store import PostStore
from fastapi import APIRouter, Depends, HTTPException

from shared import schemas
from app.controllers.dependencies import WrappedUser, get_caller_user

router = APIRouter()


@router.get("/{place_id}/icon", response_model=schemas.map.MapPinIcon)
async def get_place_icon(
    place_id: uuid.UUID,
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    return await place_store.get_place_icon(user.id, place_id)


@router.get("/{place_id}/mutualPosts", response_model=list[schemas.post.Post])
async def get_mutual_posts(
    place_id: uuid.UUID,
    post_store: PostStore = Depends(get_post_store),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    mutual_posts = await post_store.get_mutual_posts(user.id, place_id)
    if mutual_posts is None:
        raise HTTPException(404)
    return mutual_posts
