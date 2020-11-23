from typing import Union, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic.tools import parse_obj_as
from sqlalchemy.orm import Session

from app.controllers import controller, auth
from app.database import get_db
from app.models import models, schemas
from app.models.request_schemas import CreateUserRequest, UpdateUserRequest
from app.models.models import User
from app.models.schemas import PrivateUser, PublicUser
from app.models.response_schemas import CreateUserResponse, UpdateUserResponse

router = APIRouter()


def validate_user(user: models.User):
    if user is None or user.deactivated:
        raise HTTPException(404, detail="User not found")


def validate_private_account_access(user: models.User, caller_email=None):
    if user.private_account:
        authorized = any(u.email == caller_email for u in user.followers)
        if not authorized:
            raise HTTPException(403, "Not authorized")


def get_email_or_401(authorization) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(401, detail="Not authenticated")
    id_token = authorization[7:]
    user_email = auth.get_user_email(id_token)
    if user_email is None:
        raise HTTPException(401, "Not authenticated")
    return user_email


@router.post("/", response_model=CreateUserResponse)
def create_user(request: CreateUserRequest, db: Session = Depends(get_db)):
    """Create a new user.

    Args:
        request: The request to create the user. The uid should exist in Firebase and the email field should match the
        one in Firebase.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A dict with one key, "success," mapped to True if creating the user was successful and False otherwise.

    Raises:
        HTTPException: If the uid could not be found (404) or the emails did not match.
    """
    email = auth.get_email_from_uid(request.uid)
    if email is None or email != request.email:
        raise HTTPException(404, detail="Cannot create user")
    created = controller.create_user(db, email, request.username, request.first_name, request.last_name)
    return CreateUserResponse(created=created)


@router.get("/{username}", response_model=Union[PrivateUser, PublicUser])
def get_user(username: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the given user's details.

    Args:
        username: The username string.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The requested user. A PrivateUser object is returned if the caller's
        credentials match the requested username.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    user_email = get_email_or_401(authorization)
    user: models.User = controller.get_user(db, username)
    validate_user(user)
    if user.email == user_email:
        return parse_obj_as(PrivateUser, user)
    return parse_obj_as(PublicUser, user)


@router.post("/{username}", response_model=UpdateUserResponse)
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
    user_email = get_email_or_401(authorization)
    user: models.User = controller.get_user(db, username)
    validate_user(user)
    if user.email != user_email:
        raise HTTPException(403, detail="Not authorized")
    return controller.update_user(db, user, request)


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
    caller_email = get_email_or_401(authorization)
    # TODO(gmekkat): Paginate results
    user: User = controller.get_user(db, username)
    validate_user(user)
    validate_private_account_access(user=user, caller_email=caller_email)
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
    caller_email = get_email_or_401(authorization)
    # TODO(gmekkat): Paginate results
    user = controller.get_user(db, username)
    validate_user(user)
    validate_private_account_access(user=user, caller_email=caller_email)
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
    caller_email = get_email_or_401(authorization)
    # TODO(gmekkat): Paginate results
    user = controller.get_user(db, username)
    validate_user(user)
    validate_private_account_access(user=user, caller_email=caller_email)
    return user.posts


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
    caller_email = get_email_or_401(authorization)
    user = controller.get_user(db, username)
    validate_user(user)
    if user.email != caller_email:
        raise HTTPException(403, "Not authorized")
    feed = controller.get_feed(db, user, before)
    if feed is None:
        raise HTTPException(404, "Failed to load more posts")
    return feed
