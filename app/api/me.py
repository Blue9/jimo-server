import random
import uuid
from typing import Optional

import shared.stores.utils
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
from app.controllers.dependencies import get_caller_user, JimoUser
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.controllers.tasks import BackgroundTaskHandler, get_task_handler
from app.db.database import get_db
from shared.models import models

router = APIRouter()


@router.get("", response_model=schemas.user.PublicUser)
async def get_me(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Get the current user based on the auth details."""
    user = await user_store.get_user_by_uid(firebase_user.uid)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


@router.post("", response_model=schemas.user.UpdateProfileResponse, response_model_exclude_none=True)
async def update_user(
    request: schemas.user.UpdateProfileRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
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
    return response


@router.get("/preferences", response_model=schemas.user.UserPrefs)
async def get_preferences(
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get the current user's preferences."""
    user: schemas.internal.InternalUser = wrapped_user.user
    return await user_store.get_user_preferences(user.id)


@router.post("/preferences", response_model=schemas.user.UserPrefs, response_model_exclude_none=True)
async def update_preferences(
    request: schemas.user.UserPrefs,
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
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
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Set the current user's profile picture."""
    old_user: schemas.internal.InternalUser = wrapped_user.user
    image_upload = await utils.upload_image(file, old_user, firebase_user.shared_firebase, db)
    new_user, errors = await user_store.update_user(old_user.id, profile_picture_id=image_upload.id)
    if old_user.profile_picture_blob_name:
        await firebase_user.shared_firebase.delete_image(old_user.profile_picture_blob_name)
    if new_user is not None:
        return new_user
    else:
        raise HTTPException(400, detail=errors.dict() if errors else None)


@router.get("/feed", response_model=schemas.post.Feed)
async def get_feed(
    cursor: Optional[uuid.UUID] = None,
    feed_store: FeedStore = Depends(get_feed_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Get the feed for the current user."""
    page_size = 10
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
        user_store=user_store
    )
    next_cursor: Optional[uuid.UUID] = min(post.id for post in feed) if len(feed) >= page_size else None
    return schemas.post.Feed(posts=feed, cursor=next_cursor)


@router.get("/map", response_model=list[schemas.map.MapPin])
async def get_map(
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    user: schemas.internal.InternalUser = wrapped_user.user
    return await place_store.get_map(user.id)


@router.get("/mapV2", response_model=schemas.map.MapResponse)
async def get_map_v2(
    feed_store: FeedStore = Depends(get_feed_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store)
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
        user_store=user_store
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
    wrapped_user: JimoUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Get the discover feed for the current user."""
    user: schemas.internal.InternalUser = wrapped_user.user
    # Step 1: Get post ids
    post_ids = await feed_store.get_discover_feed_ids(user.id, limit=99)  # Prevent additional row on iOS
    if len(post_ids) == 0:
        return []
    # Step 2: Convert to posts
    feed = await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store
    )
    return JSONResponse(content=jsonable_encoder(feed))


@router.get("/suggested", response_model=list[schemas.user.PublicUser])
async def get_featured_users(
    user_store: UserStore = Depends(get_user_store),
    _wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get the list of featured jimo accounts."""
    featured_user_ids = await user_store.get_featured_users()
    user_map = await user_store.get_users(featured_user_ids)
    return [user_map.get(user_id) for user_id in featured_user_ids]


@router.get("/suggested-users", response_model=schemas.user.SuggestedUsersResponse)
async def get_suggested_users(
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
):
    """Get the list of suggested jimo accounts for the current user."""
    user: schemas.internal.InternalUser = wrapped_user.user
    suggested_users: list[schemas.user.SuggestedUserIdItem] = await user_store.get_suggested_users(user.id, limit=50)
    if len(suggested_users) == 0:
        return schemas.user.SuggestedUsersResponse(users=[])
    user_map = await user_store.get_users([item[0] for item in suggested_users])
    users = [schemas.user.SuggestedUserItem(user=user_map.get(user_id), num_mutual_friends=num_mutual_friends) for
             user_id, num_mutual_friends in suggested_users]
    random.shuffle(users)
    return schemas.user.SuggestedUsersResponse(users=users[:25])


@router.post("/contacts", response_model=list[schemas.user.PublicUser])
async def get_existing_users(
    request: schemas.user.PhoneNumberList,
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user)
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
    wrapped_user: JimoUser = Depends(get_caller_user)
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

    # Note: This makes N+1 queries, one for each followed user and one for the current user, we can optimize this later
    if task_handler:
        for followed in users_to_follow:
            prefs = await user_store.get_user_preferences(followed)
            if prefs.follow_notifications:
                await task_handler.notify_follow(followed, followed_by=user)
    return schemas.base.SimpleResponse(success=True)


@router.get("/saved-posts", response_model=schemas.post.Feed)
async def get_saved_posts(
    cursor: Optional[uuid.UUID] = None,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    jimo_user: JimoUser = Depends(get_caller_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Get the given user's posts."""
    page_size = 15
    # Step 1: Get post ids
    user = jimo_user.user
    post_saves = await post_store.get_saved_posts_by_user(user.id, cursor=cursor, limit=page_size)
    if len(post_saves) == 0:
        return schemas.post.Feed(posts=[], cursor=None)
    post_save_ids, post_ids = zip(*[(save.id, save.post_id) for save in post_saves])
    # Step 2: Convert to posts
    posts = await get_posts_from_post_ids(
        current_user=user,
        post_ids=post_ids,
        post_store=post_store,
        place_store=place_store,
        user_store=user_store,
        preserve_order=True,
    )
    next_cursor: Optional[uuid.UUID] = min(post_save_ids) if len(posts) >= page_size else None
    return schemas.post.Feed(posts=posts, cursor=next_cursor)
