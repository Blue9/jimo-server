import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from app.core.firebase import FirebaseUser, get_firebase_user

from app.core.types import PostId, PlaceId
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
from app.features.users.user_store import UserStore

router = APIRouter()


# NOTE: find_place is not authenticated (anonymous Firebase accounts can access)
@router.get("/matching", response_model=FindPlaceResponse)
async def find_place(
    name: str,
    latitude: float = Query(ge=-90, le=90),
    longitude: float = Query(ge=-180, le=180),
    place_store: PlaceStore = Depends(get_place_store),
    _firebase_user: FirebaseUser = Depends(get_firebase_user),
):
    # NOTE: not authenticated (anonymous Firebase accounts can access)
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
    firebase_user: FirebaseUser = Depends(get_firebase_user),
):
    """Get the details of the given place."""
    # TODO this can be optimized but it's fine for now
    place: Place | None = await place_store.get_place(place_id)
    if place is None:
        raise HTTPException(404, detail="Place not found")

    user = await user_store.get_user(uid=firebase_user.uid)
    if not user:
        return await guest_account_get_place_details(
            place=place, place_store=place_store, post_store=post_store, user_store=user_store
        )
    community_post_ids, featured_post_ids, friend_post_ids, my_save = await asyncio.gather(
        place_store.get_community_posts(place_id=place_id),
        place_store.get_featured_user_posts(place_id=place_id),
        place_store.get_friend_posts(place_id=place_id, user_id=user.id),
        place_store.get_place_save(user_id=user.id, place_id=place_id),
    )
    all_post_ids = list(set(community_post_ids + featured_post_ids + friend_post_ids))
    posts = await get_posts_from_post_ids(
        current_user=user, post_ids=all_post_ids, post_store=post_store, place_store=place_store, user_store=user_store
    )
    posts_map = {post.id: post for post in posts}
    my_post: Post | None = next((post for _id, post in posts_map.items() if post.user.id == user.id), None)
    used = {my_post.id} if my_post else set()
    used.update(featured_post_ids)
    friend_post_ids = [post_id for post_id in friend_post_ids if post_id not in used]
    used.update(friend_post_ids)
    community_post_ids = [post_id for post_id in community_post_ids if post_id not in used]

    def to_posts(post_ids: list[PostId]) -> list[Post]:
        return [posts_map[post_id] for post_id in post_ids if post_id in posts_map]

    return GetPlaceDetailsResponse(
        place=place,
        my_post=my_post,
        my_save=my_save,
        following_posts=to_posts(friend_post_ids),
        featured_posts=to_posts(featured_post_ids),
        community_posts=to_posts(community_post_ids),
    )


async def guest_account_get_place_details(
    place: Place, place_store: PlaceStore, post_store: PostStore, user_store: UserStore
) -> GetPlaceDetailsResponse:
    featured_post_ids = await place_store.get_featured_user_posts(place_id=place.id)
    posts_map = await post_store.get_posts(post_ids=featured_post_ids)
    # Note that we don't need to worry about duplicates because (as of now) users can only post
    # once per place
    user_ids = [posts_map[post_id].user_id for post_id in posts_map]
    users_map = await user_store.get_users(user_ids)
    # We use a random post ID to mess with people trying to reverse engineer our API
    featured_posts = [
        Post.construct(
            id=uuid.uuid4(),
            place=post.place,
            category=post.category,
            content=post.content,
            stars=post.stars,
            image_id=post.image_id,
            image_url=post.image_url,
            media=[],
            created_at=post.created_at,
            like_count=post.like_count,
            comment_count=post.comment_count,
            user=users_map[post.user_id].to_public(),
            liked=False,
            saved=False,
        )
        for _post_id, post in posts_map.items()
        if post.user_id in users_map
    ]
    return GetPlaceDetailsResponse(
        place=place,
        my_post=None,
        my_save=None,
        following_posts=[],
        featured_posts=featured_posts,
        community_posts=[],
    )
