import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.types import PostId, PlaceId, SimpleResponse
from app.features.map.types import DeprecatedPlaceLoadRequest, DeprecatedCustomPlaceLoadRequest
from app.features.places.entities import Place
from app.features.places.place_store import PlaceStore
from app.features.places.types import GetPlaceDetailsResponse, FindPlaceResponse
from app.features.posts.entities import Post
from app.features.posts.post_store import PostStore
from app.features.posts.post_utils import get_posts_from_post_ids
from app.features.stores import (
    get_post_store,
    get_place_store,
    get_user_store,
)
from app.features.users.dependencies import get_caller_user
from app.features.users.entities import InternalUser
from app.features.users.user_store import UserStore

router = APIRouter()


@router.get("/matching", response_model=FindPlaceResponse)
async def find_place(
    name: str,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    place_store: PlaceStore = Depends(get_place_store),
    _user: InternalUser = Depends(get_caller_user),
):
    place: Place | None = await place_store.find_place(name, latitude, longitude, search_radius_meters=100)
    if place is None:
        return {}
    return {"place": place}


@router.get("/{place_id}/details", response_model=GetPlaceDetailsResponse)
async def get_place_details(
    place_id: PlaceId,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    place: Place | None = await place_store.get_place(place_id)
    if place is None:
        raise HTTPException(404, detail="Place not found")
    community_post_ids, featured_post_ids, following_post_ids = await asyncio.gather(
        place_store.get_community_posts(place_id=place_id),
        place_store.get_featured_user_posts(place_id=place_id),
        place_store.get_friend_posts(place_id=place_id, user_id=user.id),
    )
    all_post_ids = list(set(community_post_ids + featured_post_ids + following_post_ids))
    posts = await get_posts_from_post_ids(
        current_user=user, post_ids=all_post_ids, post_store=post_store, user_store=user_store
    )
    posts_map = {post.id: post for post in posts}
    used = set(featured_post_ids)
    following_post_ids = [post_id for post_id in following_post_ids if post_id not in used]
    used |= set(following_post_ids)
    community_post_ids = [post_id for post_id in community_post_ids if post_id not in used]

    def to_posts(post_ids: list[PostId]) -> list[Post]:
        return [posts_map[post_id] for post_id in post_ids if post_id in posts_map]

    return GetPlaceDetailsResponse(
        place=place,
        community_posts=to_posts(community_post_ids),
        featured_posts=to_posts(featured_post_ids),
        following_posts=to_posts(following_post_ids),
    )


@router.post("/{place_id}/saves", response_model=SimpleResponse)
async def save_place(
    place_id: PlaceId,
    place_store: PlaceStore = Depends(get_place_store),
    user: InternalUser = Depends(get_caller_user),
):
    await place_store.save_place(user_id=user.id, place_id=place_id)
    return SimpleResponse(success=True)


@router.delete("/{place_id}/saves", response_model=SimpleResponse)
async def unsave_place(
    place_id: PlaceId,
    place_store: PlaceStore = Depends(get_place_store),
    user: InternalUser = Depends(get_caller_user),
):
    await place_store.unsave_place(user_id=user.id, place_id=place_id)
    return SimpleResponse(success=True)


# region deprecated
@router.post("/{place_id}/getMutualPostsV3/global", response_model=list[Post])
async def _deprecated_get_community_posts(
    place_id: PlaceId,
    request: DeprecatedPlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get the community posts for the given place."""
    post_ids: list[PostId] = await place_store.get_community_posts(place_id, categories=request.categories)
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        user_store=user_store,
    )


@router.post("/{place_id}/getMutualPostsV3/following", response_model=list[Post])
async def _deprecated_get_friend_posts(
    place_id: PlaceId,
    request: DeprecatedPlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get friends' posts for the given place."""
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
async def _deprecated_get_saved_posts(
    place_id: PlaceId,
    request: DeprecatedPlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get the list of posts for the given place, using the given strategy."""
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
async def _deprecated_get_custom_posts(
    place_id: PlaceId,
    request: DeprecatedCustomPlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get the list of posts for the given place."""
    post_ids: list[PostId] = await place_store.get_custom_posts(
        place_id=place_id, user_ids=request.users, categories=request.categories
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        user_store=user_store,
    )


# endregion deprecated
