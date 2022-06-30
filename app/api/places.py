import uuid

from fastapi import APIRouter, Depends
from shared.api.internal import InternalUser
from shared.api.map import PlaceLoadRequest, CustomPlaceLoadRequest
from shared.api.post import Post
from shared.map.strategy import (
    CategoryFilter,
    EveryoneFilter,
    FriendsFilter,
    SavedPostsFilter,
    UserListFilter,
)
from shared.stores.place_store import PlaceStore
from shared.stores.post_store import PostStore
from shared.stores.user_store import UserStore

from app.api.utils import (
    get_post_store,
    get_place_store,
    get_posts_from_post_ids,
    get_user_store,
)
from app.controllers.dependencies import JimoUser, get_caller_user

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
        place_id, user_filter=EveryoneFilter(), category_filter=CategoryFilter(request.categories)  # type: ignore
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
