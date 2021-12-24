import uuid
from typing import Optional, List

import shared.stores.utils
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import get_user_store, get_place_store, get_feed_store
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
    user_store: UserStore = Depends(get_user_store)
):
    """Update the current user's profile."""
    old_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
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
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Get the current user's preferences."""
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return await user_store.get_user_preferences(user.id)


@router.post("/preferences", response_model=schemas.user.UserPrefs, response_model_exclude_none=True)
async def update_preferences(
    request: schemas.user.UserPrefs,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Update the current user's preferences."""
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return await user_store.update_preferences(user.id, request)


@router.post("/photo", response_model=schemas.user.PublicUser)
async def upload_profile_picture(
    file: UploadFile = File(...),
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store)
):
    """Set the current user's profile picture."""
    old_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
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
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    feed_store: FeedStore = Depends(get_feed_store)
):
    """Get the feed for the current user."""
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    feed = await feed_store.get_feed(user.id, cursor)
    next_cursor: Optional[uuid.UUID] = min(post.id for post in feed) if len(feed) >= 50 else None
    return schemas.post.Feed(posts=feed, cursor=next_cursor)


@router.get("/map", response_model=list[schemas.place.MapPin])
async def get_map(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    place_store: PlaceStore = Depends(get_place_store)
):
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return await place_store.get_map(user.id)


@router.get("/discover", response_model=List[schemas.post.Post])
async def get_discover_feed(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    feed_store: FeedStore = Depends(get_feed_store)
):
    """Get the discover feed for the current user."""
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return JSONResponse(content=jsonable_encoder(await feed_store.get_discover_feed(user.id)))


@router.get("/suggested", response_model=List[schemas.user.PublicUser])
async def get_suggested_users(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store)
):
    """Get the list of suggested jimo accounts."""
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
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
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Get the existing users from the list of e164 formatted phone numbers."""
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
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
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    user_store: UserStore = Depends(get_user_store)
):
    """Follow the given users."""
    user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
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
