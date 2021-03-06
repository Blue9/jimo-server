from typing import Optional, List

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import users
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.post("/", response_model=schemas.user.CreateUserResponse, response_model_exclude_none=True)
def create_user(request: schemas.user.CreateUserRequest, firebase_user: FirebaseUser = Depends(get_firebase_user),
                db: Session = Depends(get_db)):
    """Create a new user.

    Args:
        request: The request to create the user. The uid should exist in Firebase.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A dict with one key, "success," mapped to True if creating the user was successful and False otherwise.

    Raises:
        HTTPException: If the auth header is invalid (401).
    """
    phone_number: Optional[str] = firebase_user.shared_firebase.get_phone_number_from_uid(firebase_user.uid)
    return users.create_user(db, firebase_user, request, phone_number=phone_number)


@router.get("/{username}", response_model=schemas.user.PublicUser)
def get_user(username: str, _firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the given user's details.

    Args:
        username: The username string.
        _firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The requested user.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    user: models.User = utils.get_user_or_raise(username, db)
    return pydantic.parse_obj_as(schemas.user.PublicUser, user)


@router.post("/{username}", response_model=schemas.user.UpdateProfileResponse, response_model_exclude_none=True)
def update_user(username: str, request: schemas.user.UpdateProfileRequest,
                firebase_user: FirebaseUser = Depends(get_firebase_user),
                db: Session = Depends(get_db)):
    """Update the given user's profile.

    Args:
        username: The username string.
        request: The request to update the user.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The updated user object.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the caller
        isn't authorized (403).
    """
    user: models.User = utils.get_user_or_raise(username, db)
    if user.uid != firebase_user.uid:
        raise HTTPException(403, detail="Not authorized")
    return users.update_user(db, user, request)


@router.get("/{username}/preferences", response_model=schemas.user.UserPrefs)
def get_preferences(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                    db: Session = Depends(get_db)):
    """Get the given user's preferences.

    Args:
        username: The username string.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The user's preferences.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the caller
        isn't authorized (403).
    """
    user: models.User = utils.get_user_or_raise(username, db)
    if user.uid != firebase_user.uid:
        raise HTTPException(403, detail="Not authorized")
    return user.preferences


@router.post("/{username}/preferences", response_model=schemas.user.UserPrefs, response_model_exclude_none=True)
def update_preferences(username: str, request: schemas.user.UserPrefs,
                       firebase_user: FirebaseUser = Depends(get_firebase_user),
                       db: Session = Depends(get_db)):
    """Update the given user's preferences.

    Args:
        username: The username string.
        request: The preferences update request.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The updated user preferences.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the caller
        isn't authorized (403).
    """
    user: models.User = utils.get_user_or_raise(username, db)
    if user.uid != firebase_user.uid:
        raise HTTPException(403, detail="Not authorized")
    return users.update_preferences(db, user, request)


@router.get("/{username}/followers", response_model=List[schemas.user.PublicUser])
def get_followers(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                  db: Session = Depends(get_db)):
    """Get the given user's followers.

    Args:
        username: The username string.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The requested user's followers as a list of PublicUser objects. This endpoint does not currently
        paginate the response.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
        privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    # TODO(gmekkat): Paginate results
    user: models.User = users.get_user(db, username)
    utils.validate_user(user)
    utils.check_can_view_user_else_raise(user=user, caller_uid=firebase_user.uid)
    return pydantic.parse_obj_as(List[schemas.user.PublicUser], user.followers)


@router.get("/{username}/following", response_model=List[schemas.user.PublicUser])
def get_following(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                  db: Session = Depends(get_db)):
    """Get the accounts that the given user follows.

    Args:
        username: The username string.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The users that the given user follows as a list of PublicUser objects. This endpoint does not currently
        paginate the response.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
        privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    # TODO(gmekkat): Paginate results
    user = users.get_user(db, username)
    utils.validate_user(user)
    utils.check_can_view_user_else_raise(user=user, caller_uid=firebase_user.uid)
    return pydantic.parse_obj_as(List[schemas.user.PublicUser], user.following)


@router.get("/{username}/posts", response_model=List[schemas.post.Post])
def get_posts(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the posts of the given user.

    Args:
        username: The username string.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The posts of the given user as a list of Post objects. This endpoint does not currently
        paginate the response.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
        privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    caller_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    # TODO(gmekkat): Paginate results
    user = users.get_user(db, username)
    utils.validate_user(user)
    utils.check_can_view_user_else_raise(user=user, caller_uid=caller_user.uid)
    posts = []
    for post in users.get_posts(db, user):
        # ORMPostWithoutUser avoids querying post.user N times
        fields = schemas.post.ORMPostWithoutUser.from_orm(post).dict()
        posts.append(schemas.post.Post(**fields, user=user, liked=caller_user in post.likes))
    return posts


@router.get("/{username}/feed", response_model=List[schemas.post.Post])
def get_feed(username: str, before: Optional[str] = None, firebase_user: FirebaseUser = Depends(get_firebase_user),
             db: Session = Depends(get_db)):
    """Get the feed for the given user.

    Args:
        username: The username string.
        before: Get all posts before this one. Returns a 404 if the post could not be found.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The feed for the given user as a list of Post objects in reverse chronological order. This endpoint returns
        at most 50 posts and can be paginated using the optional before param.
    """
    user = users.get_user(db, username)
    utils.validate_user(user)
    if user.uid != firebase_user.uid:
        raise HTTPException(403, "Not authorized")
    feed = users.get_feed(db, user, before)
    if feed is None:
        raise HTTPException(404, "Failed to load more posts")
    posts = []
    for post in feed:
        fields = schemas.post.ORMPost.from_orm(post).dict()
        posts.append(schemas.post.Post(**fields, liked=user in post.likes))
    return posts


@router.get("/{username}/discover", response_model=List[schemas.post.Post])
def get_discover_feed(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                      db: Session = Depends(get_db)):
    """Get the discover feed for the given user.

    Args:
        username: The username string.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The discover feed for the given user as a list of Post objects in reverse chronological order.
    """
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    if user.username_lower != username.lower():
        raise HTTPException(403, "Not authorized")
    discover_feed = users.get_discover_feed(db)
    posts = []
    for post in discover_feed:
        fields = schemas.post.ORMPost.from_orm(post).dict()
        posts.append(schemas.post.Post(**fields, liked=user in post.likes))
    return posts


@router.get("/{username}/suggested", response_model=List[schemas.user.PublicUser])
def get_suggested_users(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                        db: Session = Depends(get_db)):
    """Get the list of featured jimo accounts."""
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    if user.username_lower != username.lower():
        raise HTTPException(403, "Not authorized")
    featured_usernames = ["food", "jimo", "chicago", "nyc"]
    featured_users = [users.get_user(db, username) for username in featured_usernames]
    return list(filter(lambda u: u is not None, featured_users))


@router.post("/{username}/contacts", response_model=List[schemas.user.PublicUser])
def get_existing_users(username: str, request: schemas.user.PhoneNumberList,
                       firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the existing users from the list of e164 formatted phone numbers."""
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    if user.username_lower != username.lower():
        raise HTTPException(403, "Not authorized")
    if user.phone_number is not None:
        phone_numbers = [number for number in request.phone_numbers if number != user.phone_number]
    else:
        phone_numbers = request.phone_numbers
    return users.get_users_by_phone_numbers(db, phone_numbers)


@router.get("/{username}/follow_status", response_model=schemas.user.FollowUserResponse)
def follow_status(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                  db: Session = Depends(get_db)):
    """Get follow status.

    Args:
        username: The username string to check follow status.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A boolean where true indicated the user is followed and false indicates the user is not followed.
        TODO: Eventually when we add private users we can add another status for pending.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401),
        or the caller is trying check status of themself (400).
    """
    to_user = users.get_user(db, username)
    utils.validate_user(to_user)
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return schemas.user.FollowUserResponse(followed=(to_user in from_user.following))


@router.post("/{username}/follow", response_model=schemas.user.FollowUserResponse)
def follow_user(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Follow a user.

    Args:
        username: The username string to follow.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A boolean where true indicated the user is followed and false indicates the user is not followed.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), the user is already
        followed (400), or the caller is trying to follow themself (400).
    """
    to_user = users.get_user(db, username)
    utils.validate_user(to_user)
    if to_user.uid == firebase_user.uid:
        raise HTTPException(400, "Cannot follow yourself")
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return users.follow_user(db, from_user, to_user)


@router.post("/{username}/unfollow", response_model=schemas.user.FollowUserResponse)
def unfollow_user(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                  db: Session = Depends(get_db)):
    """Unfollow a user.

    Args:
        username: The username string to follow.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A boolean where true indicated the user is followed and false indicates the user is not followed.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), the user is not
        already followed (400), or the caller is trying to unfollow themself (400).
    """
    to_user = users.get_user(db, username)
    utils.validate_user(to_user)
    if to_user.uid == firebase_user.uid:
        raise HTTPException(400, "Cannot follow yourself")
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    return users.unfollow_user(db, from_user, to_user)
