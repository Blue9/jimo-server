from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from shared.api.base import SimpleResponse
from shared.api.comment import Comment, CreateCommentRequest, LikeCommentResponse
from shared.api.internal import InternalComment, InternalPost
from shared.api.type_aliases import CommentId
from shared.stores.comment_store import CommentStore
from shared.stores.place_store import PlaceStore
from shared.stores.post_store import PostStore
from shared.stores.relation_store import RelationStore
from shared.stores.user_store import UserStore

from app.api import utils
from app.api.utils import (
    get_place_store,
    get_user_store,
    get_post_store,
    get_comment_store,
    get_relation_store,
)
from app.controllers.dependencies import JimoUser, get_caller_user
from app.controllers.tasks import BackgroundTaskHandler, get_task_handler

router = APIRouter()


@router.post("", response_model=Comment)
async def create_comment(
    request: CreateCommentRequest,
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    post_store: PostStore = Depends(get_post_store),
    place_store: PlaceStore = Depends(get_place_store),
    comment_store: CommentStore = Depends(get_comment_store),
    relation_store: RelationStore = Depends(get_relation_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user = wrapped_user.user
    post = await utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=request.post_id
    )
    comment = await comment_store.create_comment(user.id, post.id, content=request.content)
    prefs = await user_store.get_user_preferences(post.user_id)
    if task_handler and user.id != post.user_id and prefs.comment_notifications:
        place_name = await place_store.get_place_name(post.place_id)
        if place_name is not None:
            await task_handler.notify_comment(post, place_name, comment.content, comment_by=user)
    return Comment(
        id=comment.id,
        user=user,
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
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user = wrapped_user.user
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
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    comment_store: CommentStore = Depends(get_comment_store),
    post_store: PostStore = Depends(get_post_store),
    user_store: UserStore = Depends(get_user_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user = wrapped_user.user
    comment: Optional[InternalComment] = await comment_store.get_comment(comment_id)
    if comment is None or not (await post_store.post_exists_and_not_deleted(comment.post_id)):
        raise HTTPException(404)
    await comment_store.like_comment(comment_id, user.id)
    if task_handler and user.id != comment.user_id:
        prefs = await user_store.get_user_preferences(comment.user_id)
        if prefs.comment_liked_notifications:
            await task_handler.notify_comment_liked(comment, liked_by=user)
    return LikeCommentResponse(likes=await comment_store.get_like_count(comment_id))


@router.delete("/{comment_id}/likes", response_model=LikeCommentResponse)
async def unlike_comment(
    comment_id: CommentId,
    comment_store: CommentStore = Depends(get_comment_store),
    post_store: PostStore = Depends(get_post_store),
    wrapped_user: JimoUser = Depends(get_caller_user),
):
    user = wrapped_user.user
    comment: Optional[InternalComment] = await comment_store.get_comment(comment_id)
    if comment is None or not (await post_store.post_exists_and_not_deleted(comment.post_id)):
        raise HTTPException(404)
    await comment_store.unlike_comment(comment_id, user.id)
    return LikeCommentResponse(likes=await comment_store.get_like_count(comment_id))
