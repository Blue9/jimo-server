import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.stores.comment_store import CommentStore
from app.stores.post_store import PostStore
from app.stores.relation_store import RelationStore
from app.stores.user_store import UserStore

router = APIRouter()


@router.post("", response_model=schemas.comment.Comment)
def create_comment(
    request: schemas.comment.CreateCommentRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    post_store: PostStore = Depends(PostStore),
    comment_store: CommentStore = Depends(CommentStore),
    relation_store: RelationStore = Depends(RelationStore),
    user_store: UserStore = Depends(UserStore)
):
    user = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post = utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=user.id, post_id=request.post_id)
    comment = comment_store.create_comment(user.id, post.id, content=request.content)
    if user_store.get_user_preferences(post.user_id).comment_notifications:
        notifications.notify_comment(db, post, post_store.get_place_name(post.id), comment.content, comment_by=user)
    return schemas.comment.Comment(
        id=comment.id,
        user=user,
        post_id=comment.post_id,
        content=comment.content,
        created_at=comment.created_at,
        like_count=0,
        liked=False
    )


@router.delete("/{comment_id}", response_model=schemas.base.SimpleResponse)
def delete_comment(
    comment_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    post_store: PostStore = Depends(PostStore),
    comment_store: CommentStore = Depends(CommentStore),
    user_store: UserStore = Depends(UserStore)
):
    user = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    comment: Optional[schemas.internal.InternalComment] = comment_store.get_comment(comment_id)
    if comment is None:
        raise HTTPException(404)
    post: Optional[schemas.internal.InternalPost] = post_store.get_post(comment.post_id)
    if post is None:
        raise HTTPException(404)
    if user.id != comment.user_id and user.id != post.user_id:
        raise HTTPException(403)
    comment_store.delete_comment(comment.id)
    return schemas.base.SimpleResponse(success=True)


@router.post("/{comment_id}/likes", response_model=schemas.comment.LikeCommentResponse)
def like_comment(
    comment_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    comment_store: CommentStore = Depends(CommentStore),
    post_store: PostStore = Depends(PostStore),
    user_store: UserStore = Depends(UserStore)
):
    user = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    comment: Optional[schemas.internal.InternalComment] = comment_store.get_comment(comment_id)
    if comment is None or not post_store.post_exists(comment.post_id):
        raise HTTPException(404)
    comment_store.like_comment(comment_id, user.id)
    if user_store.get_user_preferences(comment.user_id).comment_liked_notifications:
        notifications.notify_comment_liked(db, comment, liked_by=user)
    return schemas.comment.LikeCommentResponse(likes=comment_store.get_like_count(comment_id))


@router.delete("/{comment_id}/likes", response_model=schemas.comment.LikeCommentResponse)
def unlike_comment(
    comment_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    comment_store: CommentStore = Depends(CommentStore),
    post_store: PostStore = Depends(PostStore),
    user_store: UserStore = Depends(UserStore)
):
    user = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    comment: Optional[schemas.internal.InternalComment] = comment_store.get_comment(comment_id)
    if comment is None or not post_store.post_exists(comment.post_id):
        raise HTTPException(404)
    comment_store.unlike_comment(comment_id, user.id)
    return schemas.comment.LikeCommentResponse(likes=comment_store.get_like_count(comment_id))
