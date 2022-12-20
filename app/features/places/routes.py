from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.core.types import PostId, PlaceId
from app.features.map.types import PlaceLoadRequest, CustomPlaceLoadRequest
from app.features.places.entities import Place
from app.features.places.place_store import PlaceStore
from app.features.places.types import GetPlaceResponse
from app.features.posts.entities import Post
from app.features.posts.post_store import PostStore
from app.features.posts.post_utils import get_posts_from_post_ids
from app.features.stores import (
    get_post_store,
    get_place_store,
    get_user_store,
)
from app.features.users.dependencies import get_caller_user, JimoUser
from app.features.users.entities import InternalUser
from app.features.users.user_store import UserStore

router = APIRouter()


@router.get("", response_model=Place)
async def get_place(
    name: str,
    latitude: float,
    longitude: float,
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    _ = wrapped_user.user
    place: Place | None = await place_store.find_place(name, latitude, longitude)
    if place is None:
        raise HTTPException(404)
    return place


@router.get("/{place_id}/details", response_model=GetPlaceResponse)
async def get_place(
    place_id: PlaceId,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user = wrapped_user.user
    place: Optional[Place] = await place_store.get_place(place_id)
    if place is None:
        raise HTTPException(404, detail="Place not found")
    community_post_ids = await place_store.get_community_posts(place_id=place_id)
    following_post_ids = await place_store.get_friend_posts(place_id=place_id, user_id=user.id)
    all_post_ids = list(set(community_post_ids + following_post_ids))
    posts = await get_posts_from_post_ids(
        current_user=user, post_ids=all_post_ids, post_store=post_store, user_store=user_store
    )
    posts_map = {post.id: post for post in posts}

    def to_posts(post_ids: list[PostId]) -> list[Post]:
        return [posts_map[post_id] for post_id in post_ids if post_id in posts_map]

    return GetPlaceResponse(
        place=place, community_posts=to_posts(community_post_ids), following_posts=to_posts(following_post_ids)
    )


@router.post("/{place_id}/getMutualPostsV3/global", response_model=list[Post])
async def get_community_posts(
    place_id: PlaceId,
    request: PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the community posts for the given place."""
    user: InternalUser = wrapped_user.user
    post_ids: list[PostId] = await place_store.get_community_posts(place_id, categories=request.categories)
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        user_store=user_store,
    )


@router.post("/{place_id}/getMutualPostsV3/following", response_model=list[Post])
async def get_friend_posts(
    place_id: PlaceId,
    request: PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get friends' posts for the given place."""
    user: InternalUser = wrapped_user.user
    post_ids: list[PostId] = await place_store.get_friend_posts(
        place_id=place_id, user_id=user.id, categories=request.categories  # type: ignore
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        user_store=user_store,
    )


@router.post("/{place_id}/getMutualPostsV3/saved-posts", response_model=list[Post])
async def get_saved_posts(
    place_id: PlaceId,
    request: PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the list of posts for the given place, using the given strategy."""
    user: InternalUser = wrapped_user.user
    post_ids: list[PostId] = await place_store.get_saved_posts(
        place_id=place_id, user_id=user.id, categories=request.categories
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        user_store=user_store,
    )


@router.post("/{place_id}/getMutualPostsV3/custom", response_model=list[Post])
async def get_custom_posts(
    place_id: PlaceId,
    request: CustomPlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the list of posts for the given place."""
    user: InternalUser = wrapped_user.user
    post_ids: list[PostId] = await place_store.get_custom_posts(
        place_id=place_id, user_ids=request.users, categories=request.categories
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        user_store=user_store,
    )
