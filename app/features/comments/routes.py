from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import tasks
from app.core.database.engine import get_db
from app.core.types import SimpleResponse, CommentId
from app.features.comments.comment_store import CommentStore
from app.features.comments.entities import InternalComment
from app.features.comments.types import CreateCommentRequest, LikeCommentResponse, Comment
from app.features.posts import post_utils
from app.features.posts.entities import InternalPost
from app.features.posts.post_store import PostStore
from app.features.stores import (
    get_post_store,
    get_comment_store,
    get_relation_store,
    get_user_store,
)
from app.features.users.dependencies import get_caller_user
from app.features.users.entities import InternalUser
from app.features.users.relation_store import RelationStore
from app.features.users.user_store import UserStore

router = APIRouter()


@router.post("", response_model=Comment)
async def create_comment(
    request: CreateCommentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    post_store: PostStore = Depends(get_post_store),
    comment_store: CommentStore = Depends(get_comment_store),
    relation_store: RelationStore = Depends(get_relation_store),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    post = await post_utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=request.post_id
    )
    comment = await comment_store.create_comment(user.id, post.id, content=request.content)

    async def notification_task():
        prefs = await user_store.get_user_preferences(post.user_id)
        if user.id != post.user_id and prefs.comment_notifications:
            await tasks.notify_comment(db, post, post.place.name, comment.content, comment_by=user)

    background_tasks.add_task(notification_task)
    return Comment.construct(
        id=comment.id,
        user=user.to_public(),
        post_id=comment.post_id,
        content=comment.content,
        created_at=comment.created_at,
        like_count=0,
        liked=False,
    )


@router.delete("/{comment_id}", response_model=SimpleResponse)
async def delete_comment(
    comment_id: CommentId,
    post_store: PostStore = Depends(get_post_store),
    comment_store: CommentStore = Depends(get_comment_store),
    user: InternalUser = Depends(get_caller_user),
):
    comment: Optional[InternalComment] = await comment_store.get_comment(comment_id)
    if comment is None:
        raise HTTPException(404)
    post: Optional[InternalPost] = await post_store.get_post(comment.post_id)
    if post is None:
        raise HTTPException(404)
    if user.id != comment.user_id and user.id != post.user_id:
        raise HTTPException(403)
    await comment_store.delete_comment(comment.id)
    return SimpleResponse(success=True)


@router.post("/{comment_id}/likes", response_model=LikeCommentResponse)
async def like_comment(
    comment_id: CommentId,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    comment_store: CommentStore = Depends(get_comment_store),
    post_store: PostStore = Depends(get_post_store),
    user_store: UserStore = Depends(get_user_store),
    user: InternalUser = Depends(get_caller_user),
):
    comment: InternalComment | None = await comment_store.get_comment(comment_id)
    if comment is None or not (await post_store.post_exists(post_id=comment.post_id)):
        raise HTTPException(404)
    await comment_store.like_comment(comment_id, user.id)

    async def task():
        if comment and user.id != comment.user_id:
            prefs = await user_store.get_user_preferences(comment.user_id)
            if prefs.comment_liked_notifications:
                await tasks.notify_comment_liked(db, comment, liked_by=user)

    background_tasks.add_task(task)
    return LikeCommentResponse(likes=await comment_store.get_like_count(comment_id))


@router.delete("/{comment_id}/likes", response_model=LikeCommentResponse)
async def unlike_comment(
    comment_id: CommentId,
    comment_store: CommentStore = Depends(get_comment_store),
    post_store: PostStore = Depends(get_post_store),
    user: InternalUser = Depends(get_caller_user),
):
    comment: Optional[InternalComment] = await comment_store.get_comment(comment_id)
    if comment is None or not (await post_store.post_exists(post_id=comment.post_id)):
        raise HTTPException(404)
    await comment_store.unlike_comment(comment_id, user.id)
    return LikeCommentResponse(likes=await comment_store.get_like_count(comment_id))
