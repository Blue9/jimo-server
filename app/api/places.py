import uuid
from typing import Optional

from shared.schemas.map import MapLoadStrategy
from shared.stores.user_store import UserStore

from app.api.utils import get_post_store, get_place_store, get_posts_from_post_ids, get_user_store
from shared.stores.place_store import PlaceStore
from shared.stores.post_store import PostStore
from fastapi import APIRouter, Depends, HTTPException

from shared import schemas
from app.controllers.dependencies import JimoUser, get_caller_user

router = APIRouter()


@router.get("/{place_id}/icon", response_model=schemas.map.MapPinIcon)
async def get_place_icon(
    place_id: uuid.UUID,
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    return await place_store.get_place_icon(user.id, place_id)


@router.get("/{place_id}/mutualPosts", response_model=list[schemas.post.Post])
async def get_mutual_posts(
    place_id: uuid.UUID,
    post_store: PostStore = Depends(get_post_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    mutual_posts = await post_store.get_mutual_posts(user.id, place_id)
    if mutual_posts is None:
        raise HTTPException(404)
    return mutual_posts


@router.post("/{place_id}/getMutualPostsV3/global", response_model=list[schemas.post.Post])
async def get_all_posts_for_place(
    place_id: uuid.UUID,
    request: schemas.map.PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get the list of posts for the given place, using the given strategy."""
    user: schemas.internal.InternalUser = wrapped_user.user
    post_ids: list[uuid.UUID] = await post_store.get_mutual_posts_v3(
        user.id,
        place_id,
        user_filter=MapLoadStrategy.everyone,
        categories=request.categories
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store
    )


@router.post("/{place_id}/getMutualPostsV3/following", response_model=list[schemas.post.Post])
async def get_friend_posts_for_place(
    place_id: uuid.UUID,
    request: schemas.map.PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get the list of posts for the given place, using the given strategy."""
    user: schemas.internal.InternalUser = wrapped_user.user
    post_ids: list[uuid.UUID] = await post_store.get_mutual_posts_v3(
        user.id,
        place_id,
        user_filter=MapLoadStrategy.following,
        categories=request.categories
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store
    )


@router.post("/{place_id}/getMutualPostsV3/saved-posts", response_model=list[schemas.post.Post])
async def get_saved_posts_for_place(
    place_id: uuid.UUID,
    request: schemas.map.PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get the list of posts for the given place, using the given strategy."""
    user: schemas.internal.InternalUser = wrapped_user.user
    post_ids: list[uuid.UUID] = await post_store.get_mutual_posts_v3(
        user.id,
        place_id,
        user_filter=MapLoadStrategy.saved_posts,
        categories=request.categories
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store
    )


@router.post("/{place_id}/getMutualPostsV3/custom", response_model=list[schemas.post.Post])
async def get_custom_posts_for_place(
    place_id: uuid.UUID,
    request: schemas.map.CustomPlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get the list of posts for the given place, using the given strategy."""
    user: schemas.internal.InternalUser = wrapped_user.user
    post_ids: list[uuid.UUID] = await post_store.get_mutual_posts_v3(
        user.id,
        place_id,
        user_filter=request.users,
        categories=request.categories
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store
    )
