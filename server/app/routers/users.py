from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic.tools import parse_obj_as
from sqlalchemy.orm import Session

from app.controllers import users
from app.database import get_db
from app.models import models, schemas
from app.models.request_schemas import CreateUserRequest, UpdateUserRequest
from app.models.models import User
from app.models.schemas import PublicUser
from app.models.response_schemas import CreateUserResponse, UpdateUserResponse, FollowUserResponse
from app.routers import utils
from app.routers.utils import get_uid_or_raise, validate_user, check_can_view_user_else_raise, get_user_or_raise

router = APIRouter()


@router.post("/", response_model=CreateUserResponse)
def create_user(request: CreateUserRequest, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Create a new user.

    Args:
        request: The request to create the user. The uid should exist in Firebase.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A dict with one key, "success," mapped to True if creating the user was successful and False otherwise.

    Raises:
        HTTPException: If the auth header is invalid (401).
    """
    print("Create user")
    uid_from_auth = get_uid_or_raise(authorization)
    return users.create_user(db, uid_from_auth, request)


@router.get("/{username}", response_model=PublicUser)
def get_user(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the given user's details.

    Args:
        username: The username string.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The requested user.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    _caller_uid = get_uid_or_raise(authorization)
    user: models.User = get_user_or_raise(username, db)
    return parse_obj_as(PublicUser, user)


@router.post("/{username}", response_model=UpdateUserResponse, response_model_exclude_none=True)
def update_user(username: str, request: UpdateUserRequest, authorization: Optional[str] = Header(None),
                db: Session = Depends(get_db)):
    """Update the settings for the given user.

    Args:
        username: The username string.
        request: The request to update the user.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The updated user object and settings.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the caller
        isn't authorized (403).
    """
    user_uid = get_uid_or_raise(authorization)
    user: models.User = get_user_or_raise(username, db)
    if user.uid != user_uid:
        raise HTTPException(403, detail="Not authorized")
    return users.update_user(db, user, request)


@router.get("/{username}/followers", response_model=List[PublicUser])
def get_followers(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the given user's followers.

    Args:
        username: The username string.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The requested user's followers as a list of PublicUser objects. This endpoint does not currently
        paginate the response.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
        privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    caller_uid = get_uid_or_raise(authorization)
    # TODO(gmekkat): Paginate results
    user: User = users.get_user(db, username)
    validate_user(user)
    check_can_view_user_else_raise(user=user, caller_uid=caller_uid)
    return parse_obj_as(List[PublicUser], user.followers)


@router.get("/{username}/following", response_model=List[PublicUser])
def get_following(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the accounts that the given user follows.

    Args:
        username: The username string.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The users that the given user follows as a list of PublicUser objects. This endpoint does not currently
        paginate the response.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
        privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    caller_uid = get_uid_or_raise(authorization)
    # TODO(gmekkat): Paginate results
    user = users.get_user(db, username)
    validate_user(user)
    check_can_view_user_else_raise(user=user, caller_uid=caller_uid)
    return parse_obj_as(List[PublicUser], user.following)


@router.get("/{username}/posts", response_model=List[schemas.Post])
def get_posts(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the posts of the given user.

    Args:
        username: The username string.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The posts of the given user as a list of Post objects. This endpoint does not currently
        paginate the response.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
        privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    caller_user = utils.get_user_from_auth_or_raise(db, authorization)
    # TODO(gmekkat): Paginate results
    user = users.get_user(db, username)
    validate_user(user)
    check_can_view_user_else_raise(user=user, caller_uid=caller_user.uid)
    posts = []
    for post in users.get_posts(db, user):
        fields = schemas.ORMPost.from_orm(post).dict()
        posts.append(schemas.Post(**fields, liked=caller_user in post.likes))
    return posts


@router.get("/{username}/feed", response_model=List[schemas.Post])
def get_feed(username: str, before: Optional[str] = None, authorization: Optional[str] = Header(None),
             db: Session = Depends(get_db)):
    """Get the feed for the given user.

    Args:
        username: The username string.
        before: Get all posts before this one. Returns a 404 if the post could not be found.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The feed for the given user as a list of Post objects in reverse chronological order. This endpoint returns
        at most 50 posts and can be paginated using the optional before param.
    """
    caller_uid = get_uid_or_raise(authorization)
    user = users.get_user(db, username)
    validate_user(user)
    if user.uid != caller_uid:
        raise HTTPException(403, "Not authorized")
    feed = users.get_feed(db, user, before)
    if feed is None:
        raise HTTPException(404, "Failed to load more posts")
    posts = []
    for post in feed:
        fields = schemas.ORMPost.from_orm(post).dict()
        posts.append(schemas.Post(**fields, liked=user in post.likes))
    return posts


@router.get("/{username}/discover", response_model=List[schemas.Post])
def get_feed(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the discover feed for the given user.

    Args:
        username: The username string.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The discover feed for the given user as a list of Post objects in reverse chronological order.
    """
    user = utils.get_user_from_auth_or_raise(db, authorization)
    if user.username_lower != username.lower():
        raise HTTPException(403, "Not authorized")
    discover_feed = users.get_discover(db, user)
    posts = []
    for post in discover_feed:
        fields = schemas.ORMPost.from_orm(post).dict()
        posts.append(schemas.Post(**fields, liked=user in post.likes))
    return posts


@router.get("/{username}/follow_status", response_model=FollowUserResponse)
def follow_status(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get follow status.

    Args:
        username: The username string to check follow status.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A boolean where true indicated the user is followed and false indicates the user is not followed.
        TODO: Eventually when we add private users we can add another status for pending.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401),
        or the caller is trying check status of themself (400).
    """
    caller_uid = get_uid_or_raise(authorization)
    to_user = users.get_user(db, username)
    validate_user(to_user)
    if to_user.uid == caller_uid:
        raise HTTPException(400, "Cannot follow yourself")

    from_user = utils.get_user_from_uid_or_raise(db, caller_uid)

    return FollowUserResponse(followed=(to_user in from_user.following))


@router.post("/{username}/follow", response_model=FollowUserResponse)
def follow_user(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Follow a user.

    Args:
        username: The username string to follow.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A boolean where true indicated the user is followed and false indicates the user is not followed.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), the user is already
        followed (400), or the caller is trying to follow themself (400).
    """
    caller_uid = get_uid_or_raise(authorization)
    to_user = users.get_user(db, username)
    validate_user(to_user)
    if to_user.uid == caller_uid:
        raise HTTPException(400, "Cannot follow yourself")

    from_user = utils.get_user_from_uid_or_raise(db, caller_uid)
    if to_user in from_user.following:
        raise HTTPException(400, "Already following this user")

    return users.follow_user(db, from_user, to_user)


@router.post("/{username}/unfollow", response_model=FollowUserResponse)
def unfollow_user(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Unfollow a user.

    Args:
        username: The username string to follow.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A boolean where true indicated the user is followed and false indicates the user is not followed.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), the user is not
        already followed (400), or the caller is trying to unfollow themself (400).
    """
    caller_uid = get_uid_or_raise(authorization)
    to_user = users.get_user(db, username)
    validate_user(to_user)
    if to_user.uid == caller_uid:
        raise HTTPException(400, "Cannot follow yourself")

    from_user = utils.get_user_from_uid_or_raise(db, caller_uid)
    if to_user not in from_user.following:
        raise HTTPException(400, "Already not following this user")

    return users.unfollow_user(db, from_user, to_user)
