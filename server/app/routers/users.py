from typing import Union, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic.tools import parse_obj_as
from sqlalchemy.orm import Session

from app.controllers import controller
from app.database import get_db
from app.models import models, schemas
from app.models.schemas import PrivateUser, PublicUser

router = APIRouter()


def validate_user(user: models.User):
    if user is None or user.deactivated:
        raise HTTPException(404, detail="User not found")


@router.get("/{username}", response_model=Union[PrivateUser, PublicUser])
def get_user(username: str, db: Session = Depends(get_db)):
    """Get the given user's details.

    Args:
        username: The username string.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The requested user. A PrivateUser object is returned if the caller's
        credentials match the requested username.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    # TODO(gmekkat): Authenticate user
    user: models.User = controller.get_user(db, username)
    validate_user(user)
    # TODO(gmekkat): If user is self return PrivateUser
    if user.username == "kevin2":
        return parse_obj_as(PrivateUser, user)
    return parse_obj_as(PublicUser, user)


@router.get("/{username}/followers", response_model=List[PublicUser])
def get_followers(username: str, db: Session = Depends(get_db)):
    """Get the given user's followers.

        Args:
            username: The username string.
            db: The database session object. This object is automatically injected by FastAPI.

        Returns:
            The requested user's followers as a list of PublicUser objects. This endpoint does not currently
            paginate the response.

        Raises:
            HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
            privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    # TODO(gmekkat): Authenticate user
    # TODO(gmekkat): Paginate results
    user = controller.get_user(db, username)
    validate_user(user)
    return parse_obj_as(List[PublicUser], user.following)


@router.get("/{username}/following", response_model=List[PublicUser])
def get_following(username: str, db: Session = Depends(get_db)):
    """Get the accounts that the given user follows.

        Args:
            username: The username string.
            db: The database session object. This object is automatically injected by FastAPI.

        Returns:
            The users that the given user follows as a list of PublicUser objects. This endpoint does not currently
            paginate the response.

        Raises:
            HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
            privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    # TODO(gmekkat): Authenticate user
    # TODO(gmekkat): Paginate results
    user = controller.get_user(db, username)
    validate_user(user)
    return parse_obj_as(List[PublicUser], user.following)


@router.get("/{username}/posts", response_model=List[schemas.Post])
def get_posts(username: str, db: Session = Depends(get_db)):
    """Get the posts of the given user.

        Args:
            username: The username string.
            db: The database session object. This object is automatically injected by FastAPI.

        Returns:
            The posts of the given user as a list of Post objects. This endpoint does not currently
            paginate the response.

        Raises:
            HTTPException: If the user could not be found (404), the caller isn't authenticated (401), or the user's
            privacy settings block the caller from viewing their posts (e.g. private account) (403).
    """
    # TODO(gmekkat): Authenticate user
    # TODO(gmekkat): Paginate results
    user = controller.get_user(db, username)
    validate_user(user)
    return user.posts
