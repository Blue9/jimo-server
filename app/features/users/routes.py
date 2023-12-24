import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import tasks
from app.core.database.engine import get_db
from app.core.database.models import UserRelationRow, UserRelationType
from app.core.firebase import FirebaseUser, get_firebase_user
from app.core.types import SimpleResponse, PostId
from app.features.places.place_store import PlaceStore
from app.features.posts import post_utils
from app.features.posts.post_store import PostStore
from app.features.posts.types import PaginatedPosts
from app.features.stores import get_place_store, get_user_store, get_relation_store, get_post_store
from app.features.users.dependencies import get_caller_user
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

router = APIRouter(tags=["users"])


async def get_requested_user(
    username: str,
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store),
    caller_user: InternalUser = Depends(get_caller_user),
) -> InternalUser:
    user: InternalUser | None = await user_store.get_user(username=username)
    if (
        user is None
        or user.deleted
        or await relation_store.is_blocked(blocked_by_user_id=user.id, blocked_user_id=caller_user.id)
    ):
        raise HTTPException(404)
    return user


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
    return CreateUserResponse.model_construct(created=user.to_public() if user else None, error=error)


@router.get("/{username}", response_model=PublicUser)
async def get_user(
    requested_user: InternalUser = Depends(get_requested_user),
):
    """Get the given user's details."""
    return requested_user


@router.get("/{username}/posts", response_model=PaginatedPosts)
async def get_posts(
    cursor: Optional[uuid.UUID] = None,
    limit: Optional[int] = 15,
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    caller_user: InternalUser = Depends(get_caller_user),
    requested_user: InternalUser = Depends(get_requested_user),
):
    """Get the posts of the given user."""
    if limit not in [15, 50, 100]:
        raise HTTPException(400)
    page_size = limit
    # Step 1: Get post ids
    post_ids = await post_store.get_post_ids(requested_user.id, cursor=cursor, limit=page_size)
    if len(post_ids) == 0:
        return PaginatedPosts(posts=[], cursor=None)
    posts = await post_utils.get_posts_from_post_ids(caller_user, post_ids, post_store, place_store, user_store)
    next_cursor: Optional[PostId] = min(post.id for post in posts) if len(posts) >= page_size else None
    return PaginatedPosts(posts=posts, cursor=next_cursor)


@router.get("/{username}/relation", response_model=RelationToUser)
async def get_relation(
    db: AsyncSession = Depends(get_db),
    from_user: InternalUser = Depends(get_caller_user),
    to_user: InternalUser = Depends(get_requested_user),
):
    """Get the relationship to the given user."""
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
    user: InternalUser = Depends(get_caller_user),
    requested_user: InternalUser = Depends(get_requested_user),
):
    """Get the followers of the given user."""
    limit = 25
    user_ids, next_cursor = await relation_store.get_followers(requested_user.id, cursor, limit)
    relations = await relation_store.get_relations(user.id, user_ids)
    users_map = await user_store.get_users(user_ids)
    items = [dict(user=user, relation=relations.get(user_id)) for user_id, user in users_map.items()]
    return dict(users=items, cursor=next_cursor)


@router.get("/{username}/following", response_model=FollowFeedResponse)
async def get_following(
    cursor: Optional[uuid.UUID] = None,
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store),
    user: InternalUser = Depends(get_caller_user),
    requested_user: InternalUser = Depends(get_requested_user),
):
    """Get the given user's following."""
    limit = 25
    user_ids, next_cursor = await relation_store.get_following(requested_user.id, cursor, limit)
    relations = await relation_store.get_relations(user.id, user_ids)
    users_map = await user_store.get_users(user_ids)
    items = [dict(user=user, relation=relations.get(user_id)) for user_id, user in users_map.items()]
    return dict(users=items, cursor=next_cursor)


@router.post("/{username}/follow", response_model=FollowUserResponse)
async def follow_user(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store),
    relation_store: RelationStore = Depends(get_relation_store),
    from_user: InternalUser = Depends(get_caller_user),
    to_user: InternalUser = Depends(get_requested_user),
):
    """Follow the given user."""
    if to_user.id == from_user.id:
        raise HTTPException(400, "Cannot follow yourself")
    try:
        await relation_store.follow_user(from_user.id, to_user.id)

        async def notify_task():
            prefs = await user_store.get_user_preferences(to_user.id)
            if prefs.follow_notifications:
                await tasks.notify_follow(db, to_user.id, followed_by=from_user)

        background_tasks.add_task(notify_task)
        return FollowUserResponse(followed=True, followers=to_user.follower_count + 1)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.post("/{username}/unfollow", response_model=FollowUserResponse)
async def unfollow_user(
    relation_store: RelationStore = Depends(get_relation_store),
    from_user: InternalUser = Depends(get_caller_user),
    to_user: InternalUser = Depends(get_requested_user),
):
    """Unfollow the given user."""
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
    from_user: InternalUser = Depends(get_caller_user),
    to_block: InternalUser = Depends(get_requested_user),
):
    """Block the given user."""
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
    from_user: InternalUser = Depends(get_caller_user),
    to_user: InternalUser = Depends(get_requested_user),
):
    """Unblock the given user."""
    if from_user.id == to_user.id:
        raise HTTPException(400, detail="Cannot block yourself")
    try:
        await relation_store.unblock_user(from_user.id, to_user.id)
        return SimpleResponse(success=True)
    except ValueError as e:
        raise HTTPException(400, str(e))
