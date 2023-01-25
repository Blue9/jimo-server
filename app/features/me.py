import random
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import union_all, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import tasks
from app.core.database.engine import get_db
from app.core.database.models import UserRelationRow, UserRow, UserRelationType
from app.core.firebase import FirebaseUser, get_firebase_user
from app.core.types import PlaceId, SimpleResponse, UserId
from app.features.images import image_utils
from app.features.places import place_utils
from app.features.places.entities import Location
from app.features.places.place_store import PlaceStore
from app.features.places.types import SavePlaceRequest, SavePlaceResponse, SavedPlacesResponse
from app.features.posts.entities import Post
from app.features.posts.feed_store import FeedStore
from app.features.posts.post_store import PostStore
from app.features.posts.post_utils import get_posts_from_post_ids
from app.features.posts.types import PaginatedPosts
from app.features.stores import (
    get_place_store,
    get_user_store,
    get_post_store,
    get_feed_store,
)
from app.features.users.dependencies import get_caller_user
from app.features.users.entities import PublicUser, UserPrefs, SuggestedUserIdItem, InternalUser
from app.features.users.types import (
    UpdateProfileResponse,
    UpdateProfileRequest,
    SuggestedUsersResponse,
    SuggestedUserItem,
    UsernameList,
    PhoneNumberList,
)
from app.features.users.user_store import UserStore

router = APIRouter()


@router.get("", response_model=PublicUser)
async def get_me(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
):
    """Get the current user based on the auth details."""
    user = await user_store.get_user(uid=firebase_user.uid)
    if user is None:
        if await user_store.user_exists(uid=firebase_user.uid):
            # User has been marked as deleted
            raise HTTPException(410)
        raise HTTPException(404, "User not found")
    return user


@router.post("", response_model=UpdateProfileResponse, response_model_exclude_none=True)
async def update_user(
    request: UpdateProfileRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    old_user: InternalUser = Depends(get_caller_user),
):
    """Update the current user's profile."""
    updated_user, error = await user_store.update_user(
        old_user.id,
        username=request.username,
        first_name=request.first_name,
        last_name=request.last_name,
        profile_picture_id=request.profile_picture_id,
    )
    if old_user.profile_picture_blob_name and updated_user is not None:
        if updated_user.profile_picture_blob_name != old_user.profile_picture_blob_name:
            # Remove the old image
            await firebase_user.shared_firebase.delete_image(old_user.profile_picture_blob_name)
    response = UpdateProfileResponse(user=updated_user, error=error)  # type: ignore
    return response


@router.post("/delete", response_model=SimpleResponse)
async def delete_user(
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Mark the current user for deletion."""
    await user_store.soft_delete_user(user_id=user.id)
    return SimpleResponse(success=True)


@router.get("/preferences", response_model=UserPrefs)
async def get_preferences(
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get the current user's preferences."""
    return await user_store.get_user_preferences(user.id)


@router.post("/preferences", response_model=UserPrefs, response_model_exclude_none=True)
async def update_preferences(
    request: UserPrefs,
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Update the current user's preferences."""
    return await user_store.update_preferences(user.id, request)


@router.post("/photo", response_model=PublicUser)
async def upload_profile_picture(
    file: UploadFile = File(...),
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Set the current user's profile picture."""
    image_upload = await image_utils.upload_image(file, user, firebase_user.shared_firebase, db)
    new_user, errors = await user_store.update_user(user.id, profile_picture_id=image_upload.id)
    if user.profile_picture_blob_name:
        await firebase_user.shared_firebase.delete_image(user.profile_picture_blob_name)
    if new_user is not None:
        return new_user
    else:
        raise HTTPException(400, detail=errors.dict() if errors else None)


@router.get("/feed", response_model=PaginatedPosts)
async def get_feed(
    cursor: Optional[uuid.UUID] = None,
    feed_store: FeedStore = Depends(get_feed_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user: InternalUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store),
):
    """Get the feed for the current user."""
    page_size = 10
    # Step 1: Get post ids
    post_ids = await feed_store.get_feed_ids(user.id, cursor=cursor, limit=page_size)
    if len(post_ids) == 0:
        return PaginatedPosts(posts=[], cursor=None)
    # Step 2: Convert to posts
    feed = await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
    )
    next_cursor: Optional[uuid.UUID] = min(post.id for post in feed) if len(feed) >= page_size else None
    return PaginatedPosts(posts=feed, cursor=next_cursor)


@router.get("/discover", response_model=list[Post])
async def _deprecated_get_discover_feed(
    feed_store: FeedStore = Depends(get_feed_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user: InternalUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store),
):
    """DEPRECATED Get the discover feed for the current user."""
    # Step 1: Get post ids
    post_ids = await feed_store.get_discover_feed_ids(user.id, limit=99)  # Prevent additional row on iOS
    if len(post_ids) == 0:
        return []
    post_ids = sorted(post_ids, reverse=True)
    # Step 2: Convert to posts
    feed = await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
    )
    return feed


@router.get("/discoverV2", response_model=PaginatedPosts)
async def get_discover_feed(
    long: Optional[float] = Query(None, ge=-180, le=180),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    feed_store: FeedStore = Depends(get_feed_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    user: InternalUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store),
):
    """Get the discover feed for the current user."""
    # Step 1: Get post ids
    location = None
    if long is not None and lat is not None:
        location = Location(latitude=lat, longitude=long)
    post_ids = await feed_store.get_discover_feed_ids(user.id, location=location, limit=30)
    if len(post_ids) == 0:
        return {"posts": []}
    post_ids = sorted(post_ids, reverse=True)
    # Step 2: Convert to posts
    posts = await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
    )
    random.shuffle(posts)
    return {"posts": posts}


@router.get("/suggested", response_model=list[PublicUser])
async def get_featured_users(
    user_store: UserStore = Depends(get_user_store),
    _user: InternalUser = Depends(get_caller_user),
):
    """Get the list of featured jimo accounts."""
    featured_user_ids = await user_store.get_featured_users()
    user_map = await user_store.get_users(featured_user_ids)
    return [user_map.get(user_id) for user_id in featured_user_ids if user_id in user_map]


@router.get("/suggested-users", response_model=SuggestedUsersResponse)
async def get_suggested_users(
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get the list of suggested Jimo accounts for the current user."""
    suggested_users: list[SuggestedUserIdItem] = await user_store.get_suggested_users(user.id, limit=50)
    if len(suggested_users) == 0:
        return SuggestedUsersResponse(users=[])
    user_map = await user_store.get_users([item[0] for item in suggested_users])
    users = [
        SuggestedUserItem(user=user_map.get(user_id), num_mutual_friends=num_mutual_friends)  # type: ignore
        for user_id, num_mutual_friends in suggested_users
        if user_id in user_map
    ]
    random.shuffle(users)
    return SuggestedUsersResponse(users=users[:25])


@router.post("/contacts", response_model=list[PublicUser])
async def get_existing_users(
    request: PhoneNumberList,
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get the existing users from the list of e164 formatted phone numbers."""
    if user.phone_number is not None:
        phone_numbers = [number for number in request.phone_numbers if number != user.phone_number]
    else:
        phone_numbers = request.phone_numbers
    if len(phone_numbers) < 10:
        return []
    limit = int(len(phone_numbers) / 4)
    user_ids = await user_store.get_users_by_phone_number(phone_numbers, limit=limit)
    user_map = await user_store.get_users(user_ids)
    return [user_map.get(user_id) for user_id in user_ids if user_id in user_map]


@router.post("/following", response_model=SimpleResponse)
async def follow_many(
    request: UsernameList,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Follow the given users."""
    username_list = [username.lower() for username in request.usernames if username.lower() != user.username_lower]
    # Users to follow = all the existing users in the list that do not block us and that we do not follow or block
    followed_or_blocked_subquery = union_all(
        select(UserRelationRow.to_user_id).where(UserRelationRow.from_user_id == user.id),
        select(UserRelationRow.from_user_id).where(
            (UserRelationRow.to_user_id == user.id) & (UserRelationRow.relation == UserRelationType.blocked)
        ),
    )
    users_to_follow_query = (
        select(UserRow.id)
        .where(UserRow.username_lower.in_(username_list), ~UserRow.deleted)
        .where(UserRow.id.not_in(followed_or_blocked_subquery))
    )
    users_to_follow: list[UserId] = (await db.execute(users_to_follow_query)).scalars().all()  # type: ignore
    for to_follow in users_to_follow:
        db.add(
            UserRelationRow(
                from_user_id=user.id,
                to_user_id=to_follow,
                relation=UserRelationType.following,
            )
        )
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(400)

    # Note: This makes N queries, can optimize later
    async def task():
        for followed in users_to_follow:
            prefs = await user_store.get_user_preferences(followed)
            if prefs.follow_notifications:
                await tasks.notify_follow(db, followed, followed_by=user)

    background_tasks.add_task(task)
    return SimpleResponse(success=True)


@router.get("/saved-posts", response_model=PaginatedPosts)
async def _deprecated_get_saved_posts(
    cursor: Optional[uuid.UUID] = None,
    _user: InternalUser = Depends(get_caller_user),
):
    return PaginatedPosts(posts=[], cursor=None)


@router.get("/saved-places", response_model=SavedPlacesResponse)
async def get_saved_places(
    cursor: Optional[uuid.UUID] = None,
    place_store: PlaceStore = Depends(get_place_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Get the given user's saved places."""
    page_size = 15
    saves = await place_store.get_saved_places(user.id, cursor=cursor, limit=page_size)
    next_cursor: uuid.UUID | None = min([save.id for save in saves]) if len(saves) >= page_size else None
    return SavedPlacesResponse(saves=saves, cursor=next_cursor)


@router.post("/saved-places", response_model=SavePlaceResponse)
async def save_place(
    request: SavePlaceRequest,
    place_store: PlaceStore = Depends(get_place_store),
    user: InternalUser = Depends(get_caller_user),
):
    # We can ignore the type because of SavePlaceRequest's validation (requires that place_id or place are present)
    place_id = request.place_id or await place_utils.get_or_create_place(
        user_id=user.id, request=request.place, place_store=place_store  # type: ignore
    )
    # TODO: we don't validate request.place_id
    save = await place_store.save_place(user_id=user.id, place_id=place_id, note=request.note)
    return SavePlaceResponse(save=save, create_place_request=request.place)


@router.delete("/saved-places/{place_id}", response_model=SimpleResponse)
async def unsave_place(
    place_id: PlaceId,
    place_store: PlaceStore = Depends(get_place_store),
    user: InternalUser = Depends(get_caller_user),
):
    await place_store.unsave_place(user_id=user.id, place_id=place_id)
    return SimpleResponse(success=True)
