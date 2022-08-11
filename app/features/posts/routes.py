import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from shared.api.comment import Comment
from shared.api.internal import InternalUser, InternalPost
from shared.api.post import Post
from shared.stores.comment_store import CommentStore
from shared.stores.place_store import PlaceStore
from shared.stores.post_store import PostStore
from shared.stores.relation_store import RelationStore
from shared.stores.user_store import UserStore

from app.core.common import SimpleResponse
from app.core.firebase import FirebaseUser, get_firebase_user
from app.core.tasks import BackgroundTaskHandler, get_task_handler
from app.features import utils
from app.features.comments.types import CommentPageResponse
from app.features.posts.types import CreatePostRequest, DeletePostResponse, LikePostResponse, ReportPostRequest
from app.features.users.dependencies import get_caller_user, JimoUser
from app.features.utils import get_user_store, get_post_store, get_relation_store, get_place_store, get_comment_store
from app.utils import get_logger

router = APIRouter()
log = get_logger(__name__)


@router.get("/{post_id}", response_model=Post)
async def get_post(
    post_id: uuid.UUID,
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Get the given post."""
    current_user: InternalUser = wrapped_user.user
    post: InternalPost = await utils.get_post_and_validate_or_raise(
        post_store, relation_store, current_user.id, post_id
    )
    post_author: Optional[InternalUser] = await user_store.get_user(post.user_id)
    if post_author is None:
        log.error("Expected user to exist, found None", post.user_id)
        raise HTTPException(404)
    return Post(
        id=post.id,
        place=post.place,
        category=post.category,
        content=post.content,
        image_url=post.image_url,
        created_at=post.created_at,
        like_count=post.like_count,
        comment_count=post.comment_count,
        user=post_author,
        liked=await post_store.is_post_liked(post_id, liked_by=current_user.id),
        saved=await post_store.is_post_saved(post_id, saved_by=current_user.id),
    )


@router.post("", response_model=Post)
async def create_post(
    req: CreatePostRequest,
    place_store: PlaceStore = Depends(get_place_store),
    post_store: PostStore = Depends(get_post_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Create a new post."""
    try:
        if req.place_id is None and req.place is None:
            raise HTTPException(400, "Either place_id or place must be specified")
        user: InternalUser = wrapped_user.user
        place_id = req.place_id or await utils.get_or_create_place(user.id, req.place, place_store)  # type: ignore
        post: InternalPost = await post_store.create_post(user.id, place_id, req.category, req.content, req.image_id)
        return Post(**post.dict(), user=user, liked=False, saved=False)
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.put("/{post_id}", response_model=Post)
async def update_post(
    post_id: uuid.UUID,
    req: CreatePostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    place_store: PlaceStore = Depends(get_place_store),
    post_store: PostStore = Depends(get_post_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Update the given post."""
    try:
        user: InternalUser = wrapped_user.user
        old_post: Optional[InternalPost] = await post_store.get_post(post_id)
        if old_post is None:
            raise HTTPException(404)
        if old_post.user_id != user.id:
            raise HTTPException(403)
        if req.place_id is None and req.place is None:
            raise HTTPException(400, "Either place_id or place must be specified")
        place_id = req.place_id or await utils.get_or_create_place(user.id, req.place, place_store)  # type: ignore
        updated_post = await post_store.update_post(post_id, place_id, req.category, req.content, req.image_id)
        if old_post.image_id and old_post.image_id != updated_post.image_id:
            # Delete old image
            await firebase_user.shared_firebase.delete_image(old_post.image_blob_name)  # type: ignore
        return Post(
            **updated_post.dict(),
            user=user,
            liked=await post_store.is_post_liked(post_id, user.id),
            saved=await post_store.is_post_saved(post_id, user.id)
        )
    except ValueError as e:
        raise HTTPException(400, detail=str(e))


@router.delete("/{post_id}", response_model=DeletePostResponse)
async def delete_post(
    post_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    post_store: PostStore = Depends(get_post_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Delete the given post."""
    user: InternalUser = wrapped_user.user
    post: Optional[InternalPost] = await post_store.get_post(post_id)
    if post is not None and post.user_id == user.id:
        await post_store.delete_post(post.id)
        if post.image_blob_name is not None:
            await firebase_user.shared_firebase.make_image_private(post.image_blob_name)
        return DeletePostResponse(deleted=True)
    return DeletePostResponse(deleted=False)


@router.post("/{post_id}/likes", response_model=LikePostResponse)
async def like_post(
    post_id: uuid.UUID,
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Like the given post if the user has not already liked the post."""
    user: InternalUser = wrapped_user.user
    post = await utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    await post_store.like_post(user.id, post.id)
    # Notify the user that their post was liked if they aren't the current user
    if task_handler:
        prefs = await user_store.get_user_preferences(post.user_id)
        if user.id != post.user_id and prefs.post_liked_notifications:
            await task_handler.notify_post_liked(post, place_name=post.place.name, liked_by=user)
    return {"likes": await post_store.get_like_count(post.id)}


@router.delete("/{post_id}/likes", response_model=LikePostResponse)
async def unlike_post(
    post_id: uuid.UUID,
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Unlike the given post if the user has already liked the post."""
    user: InternalUser = wrapped_user.user
    post = await utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    await post_store.unlike_post(user.id, post.id)
    return {"likes": await post_store.get_like_count(post.id)}


@router.post("/{post_id}/save", response_model=SimpleResponse)
async def save_post(
    post_id: uuid.UUID,
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Save the given post if the user has not already saved the post."""
    user: InternalUser = wrapped_user.user
    post = await utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    await post_store.save_post(user.id, post.id)
    # Notify the user that their post was saved if they aren't the current user
    if task_handler:
        prefs = await user_store.get_user_preferences(post.user_id)
        if user.id != post.user_id and prefs.post_liked_notifications:
            await task_handler.notify_post_saved(post, place_name=post.place.name, saved_by=user)
    return {"success": True}


@router.post("/{post_id}/unsave", response_model=SimpleResponse)
async def unsave_post(
    post_id: uuid.UUID,
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Unsave the given post."""
    user: InternalUser = wrapped_user.user
    post = await utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    await post_store.unsave_post(user.id, post.id)
    return {"success": True}


@router.post("/{post_id}/report", response_model=SimpleResponse)
async def report_post(
    post_id: uuid.UUID,
    request: ReportPostRequest,
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    """Report the given post."""
    reported_by: InternalUser = wrapped_user.user
    post = await utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=reported_by.id, post_id=post_id
    )
    success = await post_store.report_post(post.id, reported_by.id, details=request.details)
    return SimpleResponse(success=success)


@router.get("/{post_id}/comments", response_model=CommentPageResponse)
async def get_comments(
    post_id: uuid.UUID,
    cursor: Optional[uuid.UUID] = None,
    post_store: PostStore = Depends(get_post_store),
    comment_store: CommentStore = Depends(get_comment_store),
    relation_store: RelationStore = Depends(get_relation_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
) -> CommentPageResponse:
    user = wrapped_user.user
    post = await utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=post_id
    )
    orm_comments, cursor = await comment_store.get_comments(post_id=post.id, cursor=cursor)
    liked_comments = await comment_store.get_liked_comments(user.id, [c.id for c in orm_comments])
    comments = [
        Comment(
            id=c.id,
            user=c.user,
            post_id=c.post_id,
            content=c.content,
            created_at=c.created_at,
            like_count=c.like_count,
            liked=c.id in liked_comments,
        )
        for c in orm_comments
    ]
    return CommentPageResponse(comments=comments, cursor=cursor)