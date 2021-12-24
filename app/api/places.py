import uuid

from app.api.utils import get_user_store, get_post_store, get_place_store
from shared.stores.place_store import PlaceStore
from shared.stores.post_store import PostStore
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends, HTTPException

from shared import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user

router = APIRouter()


@router.get("/{place_id}/icon", response_model=schemas.place.MapPinIcon)
async def get_place_icon(
    place_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    place_store: PlaceStore = Depends(get_place_store)
):
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return await place_store.get_place_icon(user.id, place_id)


@router.get("/{place_id}/mutualPosts", response_model=list[schemas.post.Post])
async def get_mutual_posts(
    place_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store)
):
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    mutual_posts = await post_store.get_mutual_posts(user.id, place_id)
    if mutual_posts is None:
        raise HTTPException(404)
    return mutual_posts
