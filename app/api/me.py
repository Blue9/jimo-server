import uuid
from typing import Optional

import shared.stores.utils
from shared.caching.users import UserCache
from shared.stores.post_store import PostStore
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import get_user_store, get_place_store, get_feed_store, get_post_store, get_posts_from_post_ids
from shared.stores.feed_store import FeedStore
from shared.stores.place_store import PlaceStore
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import union_all, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from shared import schemas
from app.api import utils
from app.controllers.dependencies import get_caller_user, WrappedUser, get_user_cache
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.controllers.tasks import BackgroundTaskHandler, get_task_handler
from app.db.database import get_db
from shared.models import models

router = APIRouter()


@router.get("", response_model=schemas.user.PublicUser)
async def get_me(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    user_cache: UserCache = Depends(get_user_cache),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler)
):
    """Get the current user based on the auth details."""
    maybe_user = await user_cache.get_user_by_uid(firebase_user.uid)
    if maybe_user:
        print("Got cached user")
        return maybe_user
    user = await user_store.get_user_by_uid(firebase_user.uid)
    if user is None:
        raise HTTPException(404, "User not found")
    if task_handler:
        await task_handler.cache_objects(user_ids=[user.id])
    print("Wrote user to cache")
    return user


@router.post("", response_model=schemas.user.UpdateProfileResponse, response_model_exclude_none=True)
async def update_user(
    request: schemas.user.UpdateProfileRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: WrappedUser = Depends(get_caller_user),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler)
):
    """Update the current user's profile."""
    old_user: schemas.internal.InternalUser = wrapped_user.user
    updated_user, error = await user_store.update_user(
        old_user.id,
        username=request.username,
        first_name=request.first_name,
        last_name=request.last_name,
        profile_picture_id=request.profile_picture_id
    )
    if old_user.profile_picture_blob_name and updated_user is not None:
        if updated_user.profile_picture_blob_name != old_user.profile_picture_blob_name:
            # Remove the old image
            await firebase_user.shared_firebase.delete_image(old_user.profile_picture_blob_name)
    response = schemas.user.UpdateProfileResponse(user=updated_user, error=error)
    if task_handler and updated_user is not None:
        await task_handler.cache_objects(user_ids=[updated_user.id])
    return response


@router.get("/preferences", response_model=schemas.user.UserPrefs)
async def get_preferences(
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    """Get the current user's preferences."""
    user: schemas.internal.InternalUser = wrapped_user.user
    return await user_store.get_user_preferences(user.id)


@router.post("/preferences", response_model=schemas.user.UserPrefs, response_model_exclude_none=True)
async def update_preferences(
    request: schemas.user.UserPrefs,
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    """Update the current user's preferences."""
    user: schemas.internal.InternalUser = wrapped_user.user
    return await user_store.update_preferences(user.id, request)


@router.post("/photo", response_model=schemas.user.PublicUser)
async def upload_profile_picture(
    file: UploadFile = File(...),
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: WrappedUser = Depends(get_caller_user),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler)
):
    """Set the current user's profile picture."""
    old_user: schemas.internal.InternalUser = wrapped_user.user
    image_upload = await utils.upload_image(file, old_user, firebase_user.shared_firebase, db)
    new_user, errors = await user_store.update_user(old_user.id, profile_picture_id=image_upload.id)
    if old_user.profile_picture_blob_name:
        await firebase_user.shared_firebase.delete_image(old_user.profile_picture_blob_name)

    if new_user is not None:
        if task_handler:
            await task_handler.cache_objects(user_ids=[new_user.id])
        return new_user
    else:
        raise HTTPException(400, detail=errors.dict() if errors else None)


@router.get("/feed", response_model=schemas.post.Feed)
async def get_feed(
    cursor: Optional[uuid.UUID] = None,
    feed_store: FeedStore = Depends(get_feed_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: WrappedUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store),
    user_cache: UserCache = Depends(get_user_cache)
):
    """Get the feed for the current user."""
    page_size = 50
    user: schemas.internal.InternalUser = wrapped_user.user
    # Step 1: Get post ids
    post_ids = await feed_store.get_feed_ids(user.id, cursor=cursor, limit=page_size)
    if len(post_ids) == 0:
        return schemas.post.Feed(posts=[], cursor=None)
    # Step 2: Convert to posts
    feed = await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
        user_cache=user_cache
    )
    next_cursor: Optional[uuid.UUID] = min(post.id for post in feed) if len(feed) >= 50 else None
    return schemas.post.Feed(posts=feed, cursor=next_cursor)


@router.get("/map", response_model=list[schemas.map.MapPin])
async def get_map(
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    return await place_store.get_map(user.id)


@router.get("/mapV2", response_model=schemas.map.MapResponse)
async def get_map_v2(
    feed_store: FeedStore = Depends(get_feed_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: WrappedUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store),
    user_cache: UserCache = Depends(get_user_cache)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    # New map endpoint returns same info as feed for now
    post_ids = await feed_store.get_feed_ids(user.id, cursor=None, limit=500)
    if len(post_ids) == 0:
        return schemas.map.MapResponse(posts=[], post_cursors_by_user={})
    posts = await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
        user_cache=user_cache
    )
    # Post cursors should be the minimum post id for each user, aka the earliest post id.
    post_cursors_by_user: dict[uuid.UUID, uuid.UUID] = {}
    for post in posts[::-1]:
        user_id = post.user.id
        if user_id not in post_cursors_by_user:
            post_cursors_by_user[user_id] = post.id
    return schemas.map.MapResponse(posts=posts, post_cursors_by_user=post_cursors_by_user)


@router.get("/discover", response_model=list[schemas.post.Post])
async def get_discover_feed(
    feed_store: FeedStore = Depends(get_feed_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: WrappedUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store),
    user_cache: UserCache = Depends(get_user_cache)
):
    """Get the discover feed for the current user."""
    user: schemas.internal.InternalUser = wrapped_user.user
    # Step 1: Get post ids
    post_ids = await feed_store.get_discover_feed_ids(user.id)
    if len(post_ids) == 0:
        return []
    # Step 2: Convert to posts
    feed = await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
        user_cache=user_cache
    )
    return JSONResponse(content=jsonable_encoder(feed))


@router.get("/suggested", response_model=list[schemas.user.PublicUser])
async def get_suggested_users(
    db: AsyncSession = Depends(get_db),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    """Get the list of suggested jimo accounts."""
    user: schemas.internal.InternalUser = wrapped_user.user
    RelationToCurrent = aliased(models.UserRelation)  # noqa
    query = select(models.User) \
        .options(*shared.stores.utils.eager_load_user_options()) \
        .join(RelationToCurrent,
              (RelationToCurrent.to_user_id == user.id) & (RelationToCurrent.from_user_id == models.User.id),
              isouter=True) \
        .where(models.User.is_featured,
               ~models.User.deleted,
               RelationToCurrent.relation.is_distinct_from(models.UserRelationType.blocked))
    return (await db.execute(query)).scalars().all()


@router.post("/contacts", response_model=list[schemas.user.PublicUser])
async def get_existing_users(
    request: schemas.user.PhoneNumberList,
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    """Get the existing users from the list of e164 formatted phone numbers."""
    user: schemas.internal.InternalUser = wrapped_user.user
    if user.phone_number is not None:
        phone_numbers = [number for number in request.phone_numbers if number != user.phone_number]
    else:
        phone_numbers = request.phone_numbers
    if len(phone_numbers) < 10:
        return []
    limit = int(len(phone_numbers) / 4)
    return await user_store.get_users_by_phone_number(user.id, phone_numbers, limit=limit)


@router.post("/following", response_model=schemas.base.SimpleResponse)
async def follow_many(
    request: schemas.user.UsernameList,
    db: AsyncSession = Depends(get_db),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: WrappedUser = Depends(get_caller_user)
):
    """Follow the given users."""
    user: schemas.internal.InternalUser = wrapped_user.user
    username_list = [username.lower() for username in request.usernames if username.lower() != user.username_lower]
    # Users to follow = all the existing users in the list that do not block us and that we do not follow or block
    followed_or_blocked_subquery = union_all(
        select(models.UserRelation.to_user_id).where(models.UserRelation.from_user_id == user.id),
        select(models.UserRelation.from_user_id).where((models.UserRelation.to_user_id == user.id) & (
            models.UserRelation.relation == models.UserRelationType.blocked))
    )
    users_to_follow_query = select(models.User.id) \
        .where(models.User.username_lower.in_(username_list), ~models.User.deleted) \
        .where(models.User.id.notin_(followed_or_blocked_subquery))
    users_to_follow: list[uuid.UUID] = (await db.execute(users_to_follow_query)).scalars().all()
    for to_follow in users_to_follow:
        db.add(models.UserRelation(
            from_user_id=user.id,
            to_user_id=to_follow,
            relation=models.UserRelationType.following
        ))
    try:
        await db.commit()
    except IntegrityError:
        raise HTTPException(400)

    if task_handler:
        await task_handler.refresh_user_field(user.id, "following_count")
        for followed in users_to_follow:
            await task_handler.refresh_user_field(followed, "follower_count")

    # Note: This makes N+1 queries, one for each followed user and one for the current user, we can optimize this later
    if task_handler:
        for followed in users_to_follow:
            prefs = await user_store.get_user_preferences(followed)
            if prefs.follow_notifications:
                await task_handler.notify_follow(followed, followed_by=user)
    return schemas.base.SimpleResponse(success=True)
