import uuid
from typing import Optional, List

from app.stores.feed_store import FeedStore
from app.stores.place_store import PlaceStore
from app.stores.user_store import UserStore
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import false, true, union_all, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased, Session

from app import schemas
from app.api import utils
from app.controllers import notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.get("", response_model=schemas.user.PublicUser)
def get_me(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore)
):
    """Get the current user based on the auth details."""
    user = user_store.get_user_by_uid(firebase_user.uid)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


@router.post("", response_model=schemas.user.UpdateProfileResponse, response_model_exclude_none=True)
def update_user(
    request: schemas.user.UpdateProfileRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore)
):
    """Update the current user's profile."""
    old_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    updated_user, error = user_store.update_user(
        old_user.id,
        username=request.username,
        first_name=request.first_name,
        last_name=request.last_name,
        profile_picture_id=request.profile_picture_id
    )
    if old_user.profile_picture_blob_name and updated_user is not None:
        if updated_user.profile_picture_blob_name != old_user.profile_picture_blob_name:
            # Remove the old image
            firebase_user.shared_firebase.delete_image(old_user.profile_picture_blob_name)
    response = schemas.user.UpdateProfileResponse(user=updated_user, error=error)
    return response


@router.get("/preferences", response_model=schemas.user.UserPrefs)
def get_preferences(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore)
):
    """Get the current user's preferences."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return user_store.get_user_preferences(user.id)


@router.post("/preferences", response_model=schemas.user.UserPrefs, response_model_exclude_none=True)
def update_preferences(
    request: schemas.user.UserPrefs,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore)
):
    """Update the current user's preferences."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return user_store.update_preferences(user.id, request)


@router.post("/photo", response_model=schemas.user.PublicUser)
def upload_profile_picture(
    file: UploadFile = File(...),
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore)
):
    """Set the current user's profile picture."""
    old_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    image_upload = utils.upload_image(file, old_user, firebase_user.shared_firebase, db)
    new_user, errors = user_store.update_user(old_user.id, profile_picture_id=image_upload.id)
    if old_user.profile_picture_blob_name:
        firebase_user.shared_firebase.delete_image(old_user.profile_picture_blob_name)
    if new_user is not None:
        return new_user
    else:
        raise HTTPException(400, detail=errors.dict() if errors else None)


@router.get("/feed", response_model=schemas.post.Feed)
def get_feed(
    cursor: Optional[uuid.UUID] = None,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    feed_store: FeedStore = Depends(FeedStore)
):
    """Get the feed for the current user."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    feed = feed_store.get_feed(user.id, cursor)
    next_cursor: Optional[uuid.UUID] = min(post.id for post in feed) if len(feed) >= 50 else None
    return schemas.post.Feed(posts=feed, cursor=next_cursor)


@router.get("/map", response_model=list[schemas.place.MapPin])
def get_map(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    place_store: PlaceStore = Depends(PlaceStore)
):
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return place_store.get_map(user.id)


@router.get("/discover", response_model=List[schemas.post.Post])
def get_discover_feed(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    feed_store: FeedStore = Depends(FeedStore)
):
    """Get the discover feed for the current user."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    return JSONResponse(content=jsonable_encoder(feed_store.get_discover_feed(user.id)))


@router.get("/suggested", response_model=List[schemas.user.PublicUser])
def get_suggested_users(
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore)
):
    """Get the list of suggested jimo accounts."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    RelationToCurrent = aliased(models.UserRelation)  # noqa
    return db.query(models.User) \
        .join(RelationToCurrent,
              (RelationToCurrent.to_user_id == user.id) & (RelationToCurrent.from_user_id == models.User.id),
              isouter=True) \
        .filter(models.User.is_featured == true(),
                models.User.deleted == false(),
                RelationToCurrent.relation.is_distinct_from(models.UserRelationType.blocked)) \
        .all()


@router.post("/contacts", response_model=list[schemas.user.PublicUser])
def get_existing_users(
    request: schemas.user.PhoneNumberList,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore)
):
    """Get the existing users from the list of e164 formatted phone numbers."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    if user.phone_number is not None:
        phone_numbers = [number for number in request.phone_numbers if number != user.phone_number]
    else:
        phone_numbers = request.phone_numbers
    return user_store.get_users_by_phone_number(user.id, phone_numbers)


@router.post("/following", response_model=schemas.base.SimpleResponse)
def follow_many(
    request: schemas.user.UsernameList,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore)
):
    """Follow the given users."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    username_list = [username.lower() for username in request.usernames if username.lower() != user.username_lower]
    # Users to follow = all the existing users in the list that do not block us and that we do not follow or block
    followed_or_blocked_subquery = union_all(
        select(models.UserRelation.to_user_id).where(models.UserRelation.from_user_id == user.id),
        select(models.UserRelation.from_user_id).where((models.UserRelation.to_user_id == user.id) | (
                models.UserRelation.relation == models.UserRelationType.blocked))
    )
    users_to_follow: list[models.User] = db \
        .query(models.User) \
        .filter(models.User.username_lower.in_(username_list), models.User.deleted == false()) \
        .filter(models.User.id.notin_(followed_or_blocked_subquery)) \
        .all()
    for to_follow in users_to_follow:
        db.add(models.UserRelation(
            from_user_id=user.id,
            to_user_id=to_follow.id,
            relation=models.UserRelationType.following
        ))
    try:
        db.commit()
    except IntegrityError:
        raise HTTPException(400)
    # Note: This makes N+1 queries, one for each followed user and one for the current user, we can optimize this later
    for followed in users_to_follow:
        if user_store.get_user_preferences(followed.id).follow_notifications:
            notifications.notify_follow(db, followed.id, followed_by=user)
    return schemas.base.SimpleResponse(success=True)
