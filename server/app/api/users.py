from typing import Optional, List

import pydantic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import users, notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.post("", response_model=schemas.user.CreateUserResponse, response_model_exclude_none=True)
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
def get_user(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Get the given user's details.

    Args:
        username: The username string.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The requested user.

    Raises:
        HTTPException: If the user could not be found (404) or the caller isn't authenticated (401).
    """
    caller_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    user: Optional[models.User] = users.get_user(db, username)
    utils.validate_user(db, caller_user=caller_user, user=user)
    return pydantic.parse_obj_as(schemas.user.PublicUser, user)


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
    user: Optional[models.User] = users.get_user(db, username)
    utils.validate_user(db, caller_user=caller_user, user=user)
    if users.is_blocked(db, blocked_by_user=caller_user, blocked_user=user):
        raise HTTPException(403)
    return users.get_posts(db, caller_user, user)


@router.get("/{username}/followStatus", response_model=schemas.user.FollowUserResponse)
def get_follow_status(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                      db: Session = Depends(get_db)):
    """Get follow status.

    Args:
        username: The username string to check follow status.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A boolean where true indicated the user is followed and false indicates the user is not followed.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401),
        or the caller is trying check status of themself (400).
    """
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    to_user = users.get_user(db, username)
    utils.validate_user(db, caller_user=from_user, user=to_user)
    relation: Optional[models.UserRelationType] = db.query(models.UserRelation.relation) \
        .filter(models.UserRelation.from_user_id == from_user.id,
                models.UserRelation.to_user_id == to_user.id) \
        .scalar()
    return {"followed": relation == models.UserRelationType.following}


@router.get("/{username}/followStatusV2", response_model=schemas.user.RelationToUser)
def get_follow_status_v2(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                         db: Session = Depends(get_db)):
    """Get the relationship to the given user."""
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    to_user = users.get_user(db, username)
    utils.validate_user(db, caller_user=from_user, user=to_user)
    relation: Optional[models.UserRelationType] = db.query(models.UserRelation.relation) \
        .filter(models.UserRelation.from_user_id == from_user.id,
                models.UserRelation.to_user_id == to_user.id) \
        .scalar()
    return schemas.user.RelationToUser(relation=relation.value if relation else None)


@router.post("/{username}/follow", response_model=schemas.user.FollowUserResponse)
def follow_user(
        username: str,
        firebase_user: FirebaseUser = Depends(get_firebase_user),
        db: Session = Depends(get_db)
):
    """Follow a user.

    Args:
        username: The username string to follow.
        background_tasks: BackgroundTasks object.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A boolean where true indicated the user is followed and false indicates the user is not followed.

    Raises:
        HTTPException: If the user could not be found (404), the caller isn't authenticated (401), the user is already
        followed (400), or the caller is trying to follow themself (400).
    """
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    to_user = users.get_user(db, username)
    if to_user == from_user:
        raise HTTPException(400, "Cannot follow yourself")
    utils.validate_user(db, caller_user=from_user, user=to_user)
    try:
        follow_response = users.follow_user(db, from_user, to_user)
        notifications.notify_follow_if_enabled(db, to_user, followed_by=from_user)
        return follow_response
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


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
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    to_user = users.get_user(db, username)
    if to_user == from_user:
        raise HTTPException(400, "Cannot follow yourself")
    utils.validate_user(db, caller_user=from_user, user=to_user)
    try:
        return users.unfollow_user(db, from_user, to_user)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{username}/block", response_model=schemas.base.SimpleResponse)
def block_user(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Block the given user."""
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    to_block = users.get_user(db, username)
    if from_user == to_block:
        raise HTTPException(400, detail="Cannot block yourself")
    utils.validate_user(db, from_user, to_block)
    try:
        return users.block_user(db, from_user, to_block)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{username}/unblock", response_model=schemas.base.SimpleResponse)
def unblock_user(username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
                 db: Session = Depends(get_db)):
    """Unblock the given user."""
    from_user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    to_user = users.get_user(db, username)
    if from_user == to_user:
        raise HTTPException(400, detail="Cannot block yourself")
    utils.validate_user(db, from_user, to_user)
    try:
        return users.unblock_user(db, from_user, to_user)
    except ValueError as e:
        raise HTTPException(400, str(e))
