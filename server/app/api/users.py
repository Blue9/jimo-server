import uuid
from typing import Optional

from app.stores.invite_store import InviteStore
from app.stores.post_store import PostStore
from app.stores.relation_store import RelationStore
from app.stores.user_store import UserStore
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


@router.post("", response_model=schemas.user.CreateUserResponse, response_model_exclude_none=True)
def create_user(
    request: schemas.user.CreateUserRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    invite_store: InviteStore = Depends(InviteStore)
):
    """Create a new user."""
    phone_number: Optional[str] = firebase_user.shared_firebase.get_phone_number_from_uid(firebase_user.uid)
    if not invite_store.is_invited(phone_number):
        return schemas.user.CreateUserResponse(
            created=None, error=schemas.user.UserFieldErrors(uid="You aren't invited yet."))
    user, error = user_store.create_user(
        uid=firebase_user.uid,
        username=request.username,
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=phone_number
    )
    return schemas.user.CreateUserResponse(created=user, error=error)


@router.get("/{username}", response_model=schemas.user.PublicUser)
def get_user(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    relation_store: RelationStore = Depends(RelationStore)
):
    """Get the given user's details."""
    caller_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    user: Optional[schemas.internal.InternalUser] = user_store.get_user_by_username(username)
    utils.validate_user(relation_store, caller_user_id=caller_user.id, user=user)
    return user


@router.get("/{username}/posts", response_model=schemas.post.Feed)
def get_posts(
    username: str,
    cursor: Optional[uuid.UUID] = None,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    relation_store: RelationStore = Depends(RelationStore),
    post_store: PostStore = Depends(PostStore)
):
    """Get the posts of the given user."""
    page_size = 50
    caller_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    user: Optional[schemas.internal.InternalUser] = user_store.get_user_by_username(username)
    utils.validate_user(relation_store, caller_user_id=caller_user.id, user=user)
    if relation_store.is_blocked(blocked_by_user_id=caller_user.id, blocked_user_id=user.id):
        raise HTTPException(403)
    posts = post_store.get_posts(caller_user.id, user, cursor=cursor, limit=page_size)
    next_cursor: Optional[uuid.UUID] = min(post.id for post in posts) if len(posts) >= page_size else None
    return schemas.post.Feed(posts=posts, cursor=next_cursor)


@router.get("/{username}/relation", response_model=schemas.user.RelationToUser)
def get_relation(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore),
    relation_store: RelationStore = Depends(RelationStore)
):
    """Get the relationship to the given user."""
    from_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    to_user = user_store.get_user_by_username(username)
    utils.validate_user(relation_store, caller_user_id=from_user.id, user=to_user)
    relation: Optional[models.UserRelationType] = db.query(models.UserRelation.relation) \
        .filter(models.UserRelation.from_user_id == from_user.id,
                models.UserRelation.to_user_id == to_user.id) \
        .scalar()
    return schemas.user.RelationToUser(relation=relation.value if relation else None)


@router.post("/{username}/follow", response_model=schemas.user.FollowUserResponse)
def follow_user(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore),
    relation_store: RelationStore = Depends(RelationStore)
):
    """Follow the given user."""
    from_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    to_user = user_store.get_user_by_username(username)
    utils.validate_user(relation_store, caller_user_id=from_user.id, user=to_user)
    if to_user.id == from_user.id:
        raise HTTPException(400, "Cannot follow yourself")
    try:
        relation_store.follow_user(from_user.id, to_user.id)
        prefs = user_store.get_user_preferences(to_user.id)
        if prefs.follow_notifications:
            notifications.notify_follow(db, to_user.id, followed_by=from_user)
        return schemas.user.FollowUserResponse(followed=True, followers=to_user.follower_count + 1)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.post("/{username}/unfollow", response_model=schemas.user.FollowUserResponse)
def unfollow_user(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    relation_store: RelationStore = Depends(RelationStore)
):
    """Unfollow the given user."""
    from_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    to_user = user_store.get_user_by_username(username)
    utils.validate_user(relation_store, caller_user_id=from_user.id, user=to_user)
    if to_user.id == from_user.id:
        raise HTTPException(400, "Cannot follow yourself")
    try:
        relation_store.unfollow_user(from_user.id, to_user.id)
        return schemas.user.FollowUserResponse(followed=False, followers=to_user.follower_count - 1)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{username}/block", response_model=schemas.base.SimpleResponse)
def block_user(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    relation_store: RelationStore = Depends(RelationStore)
):
    """Block the given user."""
    from_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    to_block = user_store.get_user_by_username(username)
    utils.validate_user(relation_store, from_user.id, to_block)
    if from_user.id == to_block.id:
        raise HTTPException(400, detail="Cannot block yourself")
    try:
        return relation_store.block_user(from_user.id, to_block.id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{username}/unblock", response_model=schemas.base.SimpleResponse)
def unblock_user(
    username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    relation_store: RelationStore = Depends(RelationStore)
):
    """Unblock the given user."""
    from_user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    to_user = user_store.get_user_by_username(username)
    utils.validate_user(relation_store, from_user.id, to_user)
    if from_user.id == to_user.id:
        raise HTTPException(400, detail="Cannot block yourself")
    try:
        return relation_store.unblock_user(from_user.id, to_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
