import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import false, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased, Session

from app import schemas
from app.api import utils
from app.controllers import users, places
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.get("", response_model=schemas.user.PrivateUser)
def get_me(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the current user based on the auth details.

    Args:
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The user.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    user = users.get_user_by_uid(db, firebase_user.uid)
    if user is None:
        raise HTTPException(404, "User not found")
    return user


@router.post("", response_model=schemas.user.UpdateProfileResponse, response_model_exclude_none=True)
def update_user(request: schemas.user.UpdateProfileRequest, firebase_user: FirebaseUser = Depends(get_firebase_user),
                db: Session = Depends(get_db)):
    """Update the current user's profile.

    Args:
        request: The request to update the user.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The updated user object.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    old_profile_picture = user.profile_picture
    response = users.update_user(db, user, request)
    if old_profile_picture and user.profile_picture_id != old_profile_picture.id:
        # Remove the old image
        firebase_user.shared_firebase.delete_image(old_profile_picture.firebase_blob_name)
    return response


@router.get("/preferences", response_model=schemas.user.UserPrefs)
def get_preferences(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the current user's preferences.

    Args:
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The user's preferences.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return user.preferences


@router.post("/preferences", response_model=schemas.user.UserPrefs, response_model_exclude_none=True)
def update_preferences(request: schemas.user.UserPrefs, firebase_user: FirebaseUser = Depends(get_firebase_user),
                       db: Session = Depends(get_db)):
    """Update the current user's preferences.

    Args:
        request: The preferences update request.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The updated user preferences.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return users.update_preferences(db, user, request)


@router.post("/photo", response_model=schemas.user.PrivateUser)
def upload_profile_picture(file: UploadFile = File(...),
                           firebase_user: FirebaseUser = Depends(get_firebase_user),
                           db: Session = Depends(get_db)):
    """Set the current user's profile picture."""
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    old_profile_picture = user.profile_picture
    image_upload = utils.upload_image(file, user, firebase_user.shared_firebase, db, override_used=True)
    user.profile_picture_id = image_upload.id
    db.commit()
    if old_profile_picture:
        firebase_user.shared_firebase.delete_image(old_profile_picture.firebase_blob_name)
    return user


@router.get("/feed", response_model=schemas.post.Feed)
def get_feed(
    cursor: Optional[uuid.UUID] = None,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db)
):
    """Get the feed for the current user.

    Args:
        cursor: Get all posts before this one. Returns a 404 if the post could not be found.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The feed for the given user as a list of Post objects in reverse chronological order. This endpoint returns
        at most 50 posts and can be paginated using the optional before param.
    """
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    feed = users.get_feed(db, user, cursor)
    next_cursor: Optional[uuid.UUID] = min(post.id for post in feed) if len(feed) >= 50 else None
    return schemas.post.Feed(posts=feed, cursor=next_cursor)


@router.get("/map", response_model=list[schemas.place.MapPin])
def get_map(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return places.get_map(db, user, limit=1000)


@router.get("/discover", response_model=List[schemas.post.Post])
def get_discover_feed(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the discover feed for the current user.

    Args:
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The discover feed for the given user as a list of Post objects in reverse chronological order.
    """
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return users.get_discover_feed(db, user=user)


@router.get("/suggested", response_model=List[schemas.user.PublicUser])
def get_suggested_users(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the list of suggested jimo accounts."""
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    RelationToCurrent = aliased(models.UserRelation)
    return db.query(models.User) \
        .join(RelationToCurrent,
              (RelationToCurrent.to_user_id == user.id) & (RelationToCurrent.from_user_id == models.User.id),
              isouter=True) \
        .filter(models.User.is_featured == true(),
                models.User.deleted == false(),
                RelationToCurrent.relation.is_distinct_from(models.UserRelationType.blocked)) \
        .all()


@router.post("/contacts", response_model=List[schemas.user.PublicUser])
def get_existing_users(request: schemas.user.PhoneNumberList, firebase_user: FirebaseUser = Depends(get_firebase_user),
                       db: Session = Depends(get_db)):
    """Get the existing users from the list of e164 formatted phone numbers."""
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    if user.phone_number is not None:
        phone_numbers = [number for number in request.phone_numbers if number != user.phone_number]
    else:
        phone_numbers = request.phone_numbers
    return users.get_users_by_phone_numbers(db, user, phone_numbers)


@router.post("/following", response_model=schemas.base.SimpleResponse)
def follow_many(request: schemas.user.UsernameList, firebase_user: FirebaseUser = Depends(get_firebase_user),
                db: Session = Depends(get_db)):
    """Follow the given users."""
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    username_list = [username.lower() for username in request.usernames if username.lower() != user.username_lower]
    # Users to follow = all the existing users in the list that do not block us and that we do not follow or block
    RelationToCurrent = aliased(models.UserRelation)
    RelationFromCurrent = aliased(models.UserRelation)
    users_to_follow = db \
        .query(models.User.id) \
        .filter(models.User.username_lower.in_(username_list), models.User.deleted == false()) \
        .join(RelationToCurrent,
              (RelationToCurrent.to_user_id == user.id) & (RelationToCurrent.from_user_id == models.User.id),
              isouter=True) \
        .join(RelationFromCurrent,
              (RelationFromCurrent.from_user_id == user.id) & (RelationFromCurrent.to_user_id == models.User.id),
              isouter=True) \
        .filter(RelationFromCurrent.relation.is_(None),
                RelationToCurrent.relation.is_distinct_from(models.UserRelationType.blocked)) \
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
    return schemas.base.SimpleResponse(success=True)
