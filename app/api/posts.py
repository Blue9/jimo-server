import uuid
from typing import Optional

from app.api.utils import get_user_store, get_post_store, get_place_store, get_relation_store, get_comment_store
from shared.stores.place_store import PlaceStore
from shared.stores.post_store import PostStore
from shared.stores.relation_store import RelationStore
from shared.stores.user_store import UserStore
from fastapi import APIRouter, HTTPException, Depends

from shared import schemas
from app.api import utils
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.controllers.tasks import BackgroundTaskHandler, get_task_handler
from shared.stores.comment_store import CommentStore

router = APIRouter()


@router.post("", response_model=schemas.post.Post)
def create_post(
    request: schemas.post.CreatePostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    place_store: PlaceStore = Depends(get_place_store),
    post_store: PostStore = Depends(get_post_store)
):
    """Create a new post."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    try:
        place = place_store.get_place(request.place)
        if place is None:
            place = place_store.create_place(request.place)
        place_store.create_or_update_place_data(user.id, place.id, request.place.region, request.place.additional_data)
        post: schemas.post.ORMPost = post_store.create_post(user.id, place.id, request)
        return schemas.post.Post(**post.dict(), liked=False)
    except ValueError as e:
        print(e)
        raise HTTPException(400, detail=str(e))


@router.delete("/{post_id}", response_model=schemas.post.DeletePostResponse)
def delete_post(
    post_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store)
):
    """Delete the given post."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post: Optional[schemas.internal.InternalPost] = post_store.get_post(post_id)
    if post is not None and post.user_id == user.id:
        post_store.delete_post(post.id)
        if post.image_blob_name is not None:
            firebase_user.shared_firebase.make_image_private(post.image_blob_name)
        return schemas.post.DeletePostResponse(deleted=True)
    return schemas.post.DeletePostResponse(deleted=False)


@router.post("/{post_id}/likes", response_model=schemas.post.LikePostResponse)
def like_post(
    post_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    task_handler: Optional[BackgroundTaskHandler] = Depends(get_task_handler),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Like the given post if the user has not already liked the post."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post = utils.get_post_and_validate_or_raise(post_store, relation_store, caller_user_id=user.id, post_id=post_id)
    post_store.like_post(user.id, post.id)
    # Notify the user that their post was liked if they aren't the current user
    if task_handler:
        if user.id != post.user_id and user_store.get_user_preferences(post.user_id).post_liked_notifications:
            task_handler.notify_post_liked(post, place_name=post_store.get_place_name(post.id), liked_by=user)
    return {"likes": post_store.get_like_count(post.id)}


@router.delete("/{post_id}/likes", response_model=schemas.post.LikePostResponse)
def unlike_post(
    post_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Unlike the given post if the user has already liked the post."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post = utils.get_post_and_validate_or_raise(post_store, relation_store, caller_user_id=user.id, post_id=post_id)
    post_store.unlike_post(user.id, post.id)
    return {"likes": post_store.get_like_count(post.id)}


@router.post("/{post_id}/report", response_model=schemas.base.SimpleResponse)
def report_post(
    post_id: uuid.UUID,
    request: schemas.post.ReportPostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(get_user_store),
    post_store: PostStore = Depends(get_post_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    """Report the given post."""
    reported_by: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post = utils.get_post_and_validate_or_raise(
        post_store, relation_store, caller_user_id=reported_by.id, post_id=post_id)
    success = post_store.report_post(post.id, reported_by.id, details=request.details)
    return schemas.base.SimpleResponse(success=success)


@router.get("/{post_id}/comments", response_model=schemas.comment.CommentPage)
def get_comments(
    post_id: uuid.UUID,
    cursor: Optional[uuid.UUID] = None,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    post_store: PostStore = Depends(get_post_store),
    user_store: UserStore = Depends(get_user_store),
    comment_store: CommentStore = Depends(get_comment_store),
    relation_store: RelationStore = Depends(get_relation_store)
):
    user = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post = utils.get_post_and_validate_or_raise(post_store, relation_store, caller_user_id=user.id, post_id=post_id)
    return comment_store.get_comments(caller_user_id=user.id, post_id=post.id, cursor=cursor)
