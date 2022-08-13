import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.engine import get_db
from app.core.database.models import UserRelationRow, UserRelationType
from app.core.firebase import FirebaseUser, get_firebase_user
from app.core.tasks import BackgroundTaskHandler, get_task_handler
from app.core.types import SimpleResponse, UserId, PostId
from app.features.posts import post_utils
from app.features.posts.post_store import PostStore
from app.features.posts.types import PostFeedResponse
from app.features.stores import get_user_store, get_relation_store, get_post_store
from app.features.users.dependencies import (
    get_caller_user,
    get_requested_user,
    JimoUser,
)
from app.features.users.entities import UserFieldErrors, PublicUser, InternalUser
from app.features.users.relation_store import RelationStore
from app.features.users.types import (
    CreateUserResponse,
    RelationToUser,
    FollowFeedResponse,
    FollowUserResponse,
    CreateUserRequest,
)
from app.features.users.user_store import UserStore

router = APIRouter()


@router.post("", response_model=CreateUserResponse, response_model_exclude_none=True)
async def create_user(
    request: CreateUserRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
):
    """Create a new user."""
    phone_number: Optional[str] = await firebase_user.shared_firebase.get_phone_number_from_uid(firebase_user.uid)
    if phone_number is None:
        email: Optional[str] = await firebase_user.shared_firebase.get_email_from_uid(firebase_user.uid)
        if email is None or not email.endswith("@jimoapp.com"):
            return CreateUserResponse(
                created=None,
                error=UserFieldErrors(uid="Invalid account information."),
            )
    user, error = await user_store.create_user(
        uid=firebase_user.uid,
        username=request.username,
        first_name=request.first_name,
        last_name=request.last_name,
        phone_number=phone_number,
    )
    return CreateUserResponse(created=user, error=error)


@router.get("/{username}", response_model=PublicUser)
async def get_user(
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Get the given user's details."""
    caller_user: InternalUser = wrapped_user.user
    user: InternalUser = requested_user.user
    return await validate_user(relation_store, caller_user_id=caller_user.id, user=user)


@router.get("/{username}/posts", response_model=PostFeedResponse)
async def get_posts(
    cursor: Optional[uuid.UUID] = None,
    limit: Optional[int] = 15,
    relation_store: RelationStore = Depends(get_relation_store),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Get the posts of the given user."""
    if limit not in [15, 50, 100]:
        raise HTTPException(400)
    page_size = limit
    caller_user: InternalUser = wrapped_user.user
    maybe_user = requested_user.user
    user = await validate_user(relation_store, caller_user_id=caller_user.id, user=maybe_user)
    if await relation_store.is_blocked(blocked_by_user_id=caller_user.id, blocked_user_id=user.id):
        raise HTTPException(403)
    # Step 1: Get post ids
    post_ids = await post_store.get_post_ids(user.id, cursor=cursor, limit=page_size)
    if len(post_ids) == 0:
        return PostFeedResponse(posts=[], cursor=None)
    posts = await post_utils.get_posts_from_post_ids(caller_user, post_ids, post_store, user_store)
    next_cursor: Optional[PostId] = min(post.id for post in posts) if len(posts) >= page_size else None
    return PostFeedResponse(posts=posts, cursor=next_cursor)


@router.get("/{username}/relation", response_model=RelationToUser)
async def get_relation(
    db: AsyncSession = Depends(get_db),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Get the relationship to the given user."""
    from_user: InternalUser = wrapped_user.user
    maybe_to_user = requested_user.user
    to_user = await validate_user(relation_store, caller_user_id=from_user.id, user=maybe_to_user)
    # TODO(gmekkat): Don't use select here
    relation_query = select(UserRelationRow.relation).where(
        UserRelationRow.from_user_id == from_user.id,
        UserRelationRow.to_user_id == to_user.id,
    )
    relation: Optional[UserRelationType] = (await db.execute(relation_query)).scalar()
    return RelationToUser(relation=relation.value if relation else None)


@router.get("/{username}/followers", response_model=FollowFeedResponse)
async def get_followers(
    cursor: Optional[uuid.UUID] = None,
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Get the followers of the given user."""
    limit = 25
    current_user: InternalUser = wrapped_user.user
    maybe_to_user = requested_user.user
    to_user = await validate_user(relation_store, caller_user_id=current_user.id, user=maybe_to_user)
    user_ids, next_cursor = await relation_store.get_followers(to_user.id, cursor, limit)
    relations = await relation_store.get_relations(current_user.id, user_ids)
    users = await user_store.get_users(user_ids)
    items = [dict(user=users[user_id], relation=relations.get(user_id)) for user_id in user_ids]
    return dict(users=items, cursor=next_cursor)


@router.get("/{username}/following", response_model=FollowFeedResponse)
async def get_following(
    cursor: Optional[uuid.UUID] = None,
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Get the given user's following."""
    limit = 25
    current_user: InternalUser = wrapped_user.user
    maybe_from_user = requested_user.user
    from_user = await validate_user(relation_store, caller_user_id=current_user.id, user=maybe_from_user)
    user_ids, next_cursor = await relation_store.get_following(from_user.id, cursor, limit)
    relations = await relation_store.get_relations(current_user.id, user_ids)
    users = await user_store.get_users(user_ids)
    items = [dict(user=users[user_id], relation=relations.get(user_id)) for user_id in user_ids]
    return dict(users=items, cursor=next_cursor)


@router.post("/{username}/follow", response_model=FollowUserResponse)
async def follow_user(
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Follow the given user."""
    from_user: InternalUser = wrapped_user.user
    maybe_to_user = requested_user.user
    to_user = await validate_user(relation_store, caller_user_id=from_user.id, user=maybe_to_user)
    if to_user.id == from_user.id:
        raise HTTPException(400, "Cannot follow yourself")
    try:
        await relation_store.follow_user(from_user.id, to_user.id)
        prefs = await user_store.get_user_preferences(to_user.id)
        if task_handler and prefs.follow_notifications:
            await task_handler.notify_follow(to_user.id, followed_by=from_user)
        return FollowUserResponse(followed=True, followers=to_user.follower_count + 1)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.post("/{username}/unfollow", response_model=FollowUserResponse)
async def unfollow_user(
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Unfollow the given user."""
    from_user: InternalUser = wrapped_user.user
    maybe_to_user = requested_user.user
    to_user = await validate_user(relation_store, caller_user_id=from_user.id, user=maybe_to_user)
    if to_user.id == from_user.id:
        raise HTTPException(400, "Cannot follow yourself")
    try:
        await relation_store.unfollow_user(from_user.id, to_user.id)
        return FollowUserResponse(followed=False, followers=to_user.follower_count - 1)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{username}/block", response_model=SimpleResponse)
async def block_user(
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Block the given user."""
    from_user: InternalUser = wrapped_user.user
    maybe_to_block = requested_user.user
    to_block = await validate_user(relation_store, from_user.id, maybe_to_block)
    if from_user.id == to_block.id:
        raise HTTPException(400, detail="Cannot block yourself")
    try:
        await relation_store.block_user(from_user.id, to_block.id)
        return SimpleResponse(success=True)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{username}/unblock", response_model=SimpleResponse)
async def unblock_user(
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
    requested_user: JimoUser = Depends(get_requested_user),
):
    """Unblock the given user."""
    from_user: InternalUser = wrapped_user.user
    maybe_to_user = requested_user.user
    to_user = await validate_user(relation_store, from_user.id, maybe_to_user)
    if from_user.id == to_user.id:
        raise HTTPException(400, detail="Cannot block yourself")
    try:
        await relation_store.unblock_user(from_user.id, to_user.id)
        return SimpleResponse(success=True)
    except ValueError as e:
        raise HTTPException(400, str(e))


async def validate_user(
    relation_store: RelationStore,
    caller_user_id: UserId,
    user: Optional[InternalUser],
) -> InternalUser:
    if (
        user is None
        or user.deleted
        or await relation_store.is_blocked(blocked_by_user_id=user.id, blocked_user_id=caller_user_id)
    ):
        raise HTTPException(404, detail="User not found")
    return user
