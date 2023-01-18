from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import tasks
from app.core.database.engine import get_db
from app.core.firebase import FirebaseUser, get_firebase_user
from app.core.types import SimpleResponse, PostId, CursorId
from app.features.comments.comment_store import CommentStore
from app.features.comments.entities import CommentWithoutLikeStatus
from app.features.comments.types import CommentPageResponse, Comment
from app.features.places import place_utils
from app.features.places.place_store import PlaceStore
from app.features.posts import post_utils
from app.features.posts.entities import Post, InternalPost
from app.features.posts.post_store import PostStore
from app.features.posts.types import (
    CreatePostRequest,
    DeletePostResponse,
    LikePostResponse,
    ReportPostRequest,
)
from app.features.stores import (
    get_user_store,
    get_post_store,
    get_relation_store,
    get_place_store,
    get_comment_store,
)
from app.features.users.dependencies import get_caller_user
from app.features.users.entities import InternalUser
from app.features.users.relation_store import RelationStore
from app.features.users.user_store import UserStore
from app.utils import get_logger

router = APIRouter()
log = get_logger(__name__)


@router.get("/{post_id}", response_model=Post)
async def get_post(
    post_id: PostId,
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    current_user: InternalUser = Depends(get_caller_user),
):
    """Get the given post."""
    post: InternalPost = await post_utils.get_post_and_validate_or_raise(
        post_store, relation_store, current_user.id, post_id
    )
    post_author: Optional[InternalUser] = await user_store.get_user(user_id=post.user_id)
    if post_author is None:
        log.error("Expected user to exist, found None", post.user_id)
        raise HTTPException(404)
    return Post.construct(
        id=post.id,
        place=post.place,
        category=post.category,
        content=post.content,
        image_url=post.image_url,
        created_at=post.created_at,
        like_count=post.like_count,
        comment_count=post.comment_count,
        user=post_author.to_public(),
        liked=await post_store.is_post_liked(post_id, liked_by=current_user.id),
        saved=await post_store.is_post_saved(post_id, saved_by=current_user.id),
    )


@router.post("", response_model=Post)
async def create_post(
    request: CreatePostRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    place_store: PlaceStore = Depends(get_place_store),
    post_store: PostStore = Depends(get_post_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Create a new post."""
    try:
        if request.place_id:
            place_id = request.place_id
        elif request.place:
            place_id = await place_utils.get_or_create_place(user.id, request.place, place_store)
        else:
            raise HTTPException(400, "Either place_id or place must be specified")
        post: InternalPost = await post_store.create_post(
            user.id, place_id, request.category, request.content, request.image_id
        )
        background_tasks.add_task(tasks.slack_post_created, user.username, post)
        background_tasks.add_task(tasks.notify_post_created, db, post, user)
        return Post(**post.dict(), user=user.to_public(), liked=False, saved=False)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.put("/{post_id}", response_model=Post)
async def update_post(
    post_id: PostId,
    req: CreatePostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    place_store: PlaceStore = Depends(get_place_store),
    post_store: PostStore = Depends(get_post_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Update the given post."""
    try:
        old_post: Optional[InternalPost] = await post_store.get_post(post_id)
        if old_post is None:
            raise HTTPException(404)
        if old_post.user_id != user.id:
            raise HTTPException(403)
        if req.place_id:
            place_id = req.place_id
        elif req.place:
            place_id = await place_utils.get_or_create_place(user.id, req.place, place_store)
        else:
            raise HTTPException(400, "Either place_id or place must be specified")
        updated_post = await post_store.update_post(post_id, place_id, req.category, req.content, req.image_id)
        if old_post.image_id and old_post.image_id != updated_post.image_id:
            # Delete old image
            await firebase_user.shared_firebase.delete_image(old_post.image_blob_name)  # type: ignore
        return Post(
            **updated_post.dict(),
            user=user.to_public(),
            liked=await post_store.is_post_liked(post_id, user.id),
            saved=await post_store.is_post_saved(post_id, user.id)
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.delete("/{post_id}", response_model=DeletePostResponse)
async def delete_post(
    post_id: PostId,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    post_store: PostStore = Depends(get_post_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Delete the given post."""
    post: Optional[InternalPost] = await post_store.get_post(post_id)
    if post is not None and post.user_id == user.id:
        await post_store.delete_post(post.id)
        if post.image_blob_name is not None:
            await firebase_user.shared_firebase.delete_image(post.image_blob_name)
        return DeletePostResponse(deleted=True)
    return DeletePostResponse(deleted=False)


@router.post("/{post_id}/likes", response_model=LikePostResponse)
async def like_post(
    post_id: PostId,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Like the given post if the user has not already liked the post."""
    post = await post_utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    await post_store.like_post(user.id, post.id)

    async def task():
        # Notify the user that their post was liked if they aren't the current user
        prefs = await user_store.get_user_preferences(post.user_id)
        if user.id != post.user_id and prefs.post_liked_notifications:
            await tasks.notify_post_liked(db, post, place_name=post.place.name, liked_by=user)

    background_tasks.add_task(task)
    return {"likes": await post_store.get_like_count(post.id)}


@router.delete("/{post_id}/likes", response_model=LikePostResponse)
async def unlike_post(
    post_id: PostId,
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Unlike the given post if the user has already liked the post."""
    post = await post_utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    await post_store.unlike_post(user.id, post.id)
    return {"likes": await post_store.get_like_count(post.id)}


@router.post("/{post_id}/save", response_model=SimpleResponse)
async def save_post(
    post_id: PostId,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    relation_store: RelationStore = Depends(get_relation_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Save the given post if the user has not already saved the post."""
    post = await post_utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    await post_store.save_post(user.id, post.id)
    # TODO(gmekkat): Remove after migrating to saved places
    await place_store.save_place(user_id=user.id, place_id=post.place.id)
    return {"success": True}


@router.post("/{post_id}/unsave", response_model=SimpleResponse)
async def unsave_post(
    post_id: PostId,
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    relation_store: RelationStore = Depends(get_relation_store),
    user: InternalUser = Depends(get_caller_user),
):
    """Unsave the given post."""
    post: InternalPost = await post_utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    await post_store.unsave_post(user.id, post.id)
    # TODO(gmekkat): Remove after migrating to saved places
    await place_store.unsave_place(user_id=user.id, place_id=post.place.id)
    return {"success": True}


@router.post("/{post_id}/report", response_model=SimpleResponse)
async def report_post(
    post_id: PostId,
    request: ReportPostRequest,
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    reported_by: InternalUser = Depends(get_caller_user),
):
    """Report the given post."""
    post = await post_utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=reported_by.id, post_id=post_id
    )
    success = await post_store.report_post(post.id, reported_by.id, details=request.details)
    return SimpleResponse(success=success)


@router.get("/{post_id}/comments", response_model=CommentPageResponse)
async def get_comments(
    post_id: PostId,
    cursor: Optional[CursorId] = None,
    post_store: PostStore = Depends(get_post_store),
    comment_store: CommentStore = Depends(get_comment_store),
    relation_store: RelationStore = Depends(get_relation_store),
    user: InternalUser = Depends(get_caller_user),
) -> CommentPageResponse:
    post = await post_utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    page_limit = 10
    comments_without_likes: list[CommentWithoutLikeStatus] = await comment_store.get_comments(
        post_id=post.id, after_comment_id=cursor, limit=page_limit
    )
    liked_comments = await comment_store.get_liked_comments(user.id, [c.id for c in comments_without_likes])
    comments = [
        Comment.construct(
            id=c.id,
            user=c.user,
            post_id=c.post_id,
            content=c.content,
            created_at=c.created_at,
            like_count=c.like_count,
            liked=c.id in liked_comments,
        )
        for c in comments_without_likes
    ]
    cursor = comments_without_likes[-1].id if len(comments_without_likes) == page_limit else None
    return CommentPageResponse(comments=comments, cursor=cursor)
