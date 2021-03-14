from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

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


@router.get("/feed", response_model=List[schemas.post.Post])
def get_feed(before: Optional[str] = None, firebase_user: FirebaseUser = Depends(get_firebase_user),
             db: Session = Depends(get_db)):
    """Get the feed for the current user.

    Args:
        before: Get all posts before this one. Returns a 404 if the post could not be found.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The feed for the given user as a list of Post objects in reverse chronological order. This endpoint returns
        at most 50 posts and can be paginated using the optional before param.
    """
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    feed = users.get_feed(db, user, before)
    if feed is None:
        raise HTTPException(404, "Failed to load more posts")
    posts = []
    for post in feed:
        fields = schemas.post.ORMPost.from_orm(post).dict()
        posts.append(schemas.post.Post(**fields, liked=user in post.likes))
    return posts


@router.get("/map", response_model=list[schemas.post.Post])
def get_map(firebase_user: FirebaseUser = Depends(get_firebase_user),
            db: Session = Depends(get_db)) -> list[schemas.post.Post]:
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    utils.validate_user(user)
    return places.get_map(db, user)


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
    discover_feed = users.get_discover_feed(db)
    posts = []
    for post in discover_feed:
        fields = schemas.post.ORMPost.from_orm(post).dict()
        posts.append(schemas.post.Post(**fields, liked=user in post.likes))
    return posts


@router.get("/suggested", response_model=List[schemas.user.PublicUser])
def get_suggested_users(firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the list of featured jimo accounts."""
    _ = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    # TODO: move to table
    featured_usernames = ["food", "jimo", "chicago", "nyc"]
    featured_users = [users.get_user(db, username) for username in featured_usernames]
    return list(filter(lambda u: u is not None, featured_users))


@router.post("/contacts", response_model=List[schemas.user.PublicUser])
def get_existing_users(request: schemas.user.PhoneNumberList, firebase_user: FirebaseUser = Depends(get_firebase_user),
                       db: Session = Depends(get_db)):
    """Get the existing users from the list of e164 formatted phone numbers."""
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    if user.phone_number is not None:
        phone_numbers = [number for number in request.phone_numbers if number != user.phone_number]
    else:
        phone_numbers = request.phone_numbers
    return users.get_users_by_phone_numbers(db, phone_numbers)
