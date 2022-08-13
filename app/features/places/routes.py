import uuid

from fastapi import APIRouter, Depends

from app.core.internal import InternalUser
from app.features.map.filters import FriendsFilter, SavedPostsFilter, UserListFilter, CategoryFilter, EveryoneFilter
from app.features.map.types import PlaceLoadRequest, CustomPlaceLoadRequest
from app.features.places.place_store import PlaceStore
from app.features.posts.entities import Post
from app.features.posts.post_store import PostStore
from app.features.users.dependencies import get_caller_user, JimoUser
from app.features.users.user_store import UserStore
from app.features.utils import (
    get_post_store,
    get_place_store,
    get_user_store,
    get_posts_from_post_ids,
)

router = APIRouter()


@router.post("/{place_id}/getMutualPostsV3/global", response_model=list[Post])
async def get_all_posts_for_place(
    place_id: uuid.UUID,
    request: PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the list of posts for the given place, using the given strategy."""
    user: InternalUser = wrapped_user.user
    post_ids: list[uuid.UUID] = await post_store.get_mutual_posts_v3(
        place_id, user_filter=EveryoneFilter(), category_filter=CategoryFilter(request.categories)
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
    )


@router.post("/{place_id}/getMutualPostsV3/following", response_model=list[Post])
async def get_friend_posts_for_place(
    place_id: uuid.UUID,
    request: PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the list of posts for the given place, using the given strategy."""
    user: InternalUser = wrapped_user.user
    post_ids: list[uuid.UUID] = await post_store.get_mutual_posts_v3(
        place_id,
        user_filter=FriendsFilter(user_id=user.id),
        category_filter=CategoryFilter(request.categories),  # type: ignore
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
    )


@router.post("/{place_id}/getMutualPostsV3/saved-posts", response_model=list[Post])
async def get_saved_posts_for_place(
    place_id: uuid.UUID,
    request: PlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the list of posts for the given place, using the given strategy."""
    user: InternalUser = wrapped_user.user
    post_ids: list[uuid.UUID] = await post_store.get_mutual_posts_v3(
        place_id,
        user_filter=SavedPostsFilter(user_id=user.id),
        category_filter=CategoryFilter(request.categories),  # type: ignore
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
    )


@router.post("/{place_id}/getMutualPostsV3/custom", response_model=list[Post])
async def get_custom_posts_for_place(
    place_id: uuid.UUID,
    request: CustomPlaceLoadRequest,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the list of posts for the given place."""
    user: InternalUser = wrapped_user.user
    post_ids: list[uuid.UUID] = await post_store.get_mutual_posts_v3(
        place_id,
        user_filter=UserListFilter(user_ids=request.users),
        category_filter=CategoryFilter(request.categories),  # type: ignore
    )
    return await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
    )
