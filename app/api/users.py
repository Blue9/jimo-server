import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.utils import get_user_store, get_relation_store, get_post_store
from shared.stores.post_store import PostStore
from shared.stores.relation_store import RelationStore
from shared.stores.user_store import UserStore
from fastapi import APIRouter, Depends, HTTPException

from shared import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.controllers.tasks import BackgroundTaskHandler, get_task_handler
from app.db.database import get_db
from shared.models import models

router = APIRouter()


@router.post("", response_model=schemas.user.CreateUserResponse, response_model_exclude_none=True)
async def create_user(
    request: schemas.user.CreateUserRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store)
):
    """Create a new user."""
    phone_number: Optional[str] = await firebase_user.shared_firebase.get_phone_number_from_uid(firebase_user.uid)
    if phone_number is None:
        return schemas.user.CreateUserResponse(
            created=None, error=schemas.user.UserFieldErrors(uid="Invalid account information."))
    user, error = await user_store.create_user(
        uid=firebase_user.uid,
        username=request.username,
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=phone_number
    )
    return schemas.user.CreateUserResponse(created=user, error=error)


@router.get("/{username}", response_model=schemas.user.PublicUser)
async def get_user(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Get the given user's details."""
    caller_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    user: Optional[schemas.internal.InternalUser] = await user_store.get_user_by_username(username)
    return await utils.validate_user(relation_store, caller_user_id=caller_user.id, user=user)


@router.get("/{username}/posts", response_model=schemas.post.Feed)
async def get_posts(
    username: str,
    cursor: Optional[uuid.UUID] = None,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store),
    post_store: PostStore = Depends(get_post_store)
):
    """Get the posts of the given user."""
    page_size = 50
    caller_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    maybe_user = await user_store.get_user_by_username(username)
    user = await utils.validate_user(relation_store, caller_user_id=caller_user.id, user=maybe_user)
    if await relation_store.is_blocked(blocked_by_user_id=caller_user.id, blocked_user_id=user.id):
        raise HTTPException(403)
    posts = await post_store.get_posts(caller_user.id, user, cursor=cursor, limit=page_size)
    next_cursor: Optional[uuid.UUID] = min(post.id for post in posts) if len(posts) >= page_size else None
    return schemas.post.Feed(posts=posts, cursor=next_cursor)


@router.get("/{username}/relation", response_model=schemas.user.RelationToUser)
async def get_relation(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Get the relationship to the given user."""
    from_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    maybe_to_user = await user_store.get_user_by_username(username)
    to_user = await utils.validate_user(relation_store, caller_user_id=from_user.id, user=maybe_to_user)
    relation_query = select(models.UserRelation.relation) \
        .where(models.UserRelation.from_user_id == from_user.id, models.UserRelation.to_user_id == to_user.id)
    relation: Optional[models.UserRelationType] = (await db.execute(relation_query)).scalar()
    return schemas.user.RelationToUser(relation=relation.value if relation else None)


@router.get("/{username}/followers", response_model=schemas.user.FollowFeedResponse)
async def get_followers(
    username: str,
    cursor: Optional[uuid.UUID] = None,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Get the followers of the given user."""
    limit = 50
    current_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    maybe_to_user = await user_store.get_user_by_username(username)
    to_user = await utils.validate_user(relation_store, caller_user_id=current_user.id, user=maybe_to_user)

    users, next_cursor = await user_store.get_followers(to_user.id, cursor, limit)
    relations = await relation_store.get_relations(current_user.id, [user.id for user in users])
    items = [schemas.user.FollowFeedItem(user=user, relation=relations.get(user.id)) for user in users]
    return schemas.user.FollowFeedResponse(users=items, cursor=next_cursor)


@router.get("/{username}/following", response_model=schemas.user.FollowFeedResponse)
async def get_following(
    username: str,
    cursor: Optional[uuid.UUID] = None,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store),
):
    """Get the given user's following."""
    limit = 50
    current_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    maybe_to_user = await user_store.get_user_by_username(username)
    to_user = await utils.validate_user(relation_store, caller_user_id=current_user.id, user=maybe_to_user)

    users, next_cursor = await user_store.get_following(to_user.id, cursor, limit)
    relations = await relation_store.get_relations(current_user.id, [user.id for user in users])
    items = [schemas.user.FollowFeedItem(user=user, relation=relations.get(user.id)) for user in users]
    return schemas.user.FollowFeedResponse(users=items, cursor=next_cursor)


@router.post("/{username}/follow", response_model=schemas.user.FollowUserResponse)
async def follow_user(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Follow the given user."""
    from_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    maybe_to_user = await user_store.get_user_by_username(username)
    to_user = await utils.validate_user(relation_store, caller_user_id=from_user.id, user=maybe_to_user)
    if to_user.id == from_user.id:
        raise HTTPException(400, "Cannot follow yourself")
    try:
        await relation_store.follow_user(from_user.id, to_user.id)
        prefs = await user_store.get_user_preferences(to_user.id)
        if task_handler and prefs.follow_notifications:
            await task_handler.notify_follow(to_user.id, followed_by=from_user)
        return schemas.user.FollowUserResponse(followed=True, followers=to_user.follower_count + 1)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.post("/{username}/unfollow", response_model=schemas.user.FollowUserResponse)
async def unfollow_user(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Unfollow the given user."""
    from_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    maybe_to_user = await user_store.get_user_by_username(username)
    to_user = await utils.validate_user(relation_store, caller_user_id=from_user.id, user=maybe_to_user)
    if to_user.id == from_user.id:
        raise HTTPException(400, "Cannot follow yourself")
    try:
        await relation_store.unfollow_user(from_user.id, to_user.id)
        return schemas.user.FollowUserResponse(followed=False, followers=to_user.follower_count - 1)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{username}/block", response_model=schemas.base.SimpleResponse)
async def block_user(
    username: str,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Block the given user."""
    from_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    maybe_to_block = await user_store.get_user_by_username(username)
    to_block = await utils.validate_user(relation_store, from_user.id, maybe_to_block)
    if from_user.id == to_block.id:
        raise HTTPException(400, detail="Cannot block yourself")
    try:
        return await relation_store.block_user(from_user.id, to_block.id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{username}/unblock", response_model=schemas.base.SimpleResponse)
async def unblock_user(
    username: str, firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Unblock the given user."""
    from_user: schemas.internal.InternalUser = await utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    maybe_to_user = await user_store.get_user_by_username(username)
    to_user = await utils.validate_user(relation_store, from_user.id, maybe_to_user)
    if from_user.id == to_user.id:
        raise HTTPException(400, detail="Cannot block yourself")
    try:
        return await relation_store.unblock_user(from_user.id, to_user.id)
    except ValueError as e:
        raise HTTPException(400, str(e))
