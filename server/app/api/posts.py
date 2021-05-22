import uuid
from typing import Optional

from app.stores.place_store import PlaceStore
from app.stores.post_store import PostStore
from app.stores.user_store import UserStore
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import false
from sqlalchemy.orm import aliased, Session

from app import schemas
from app.api import utils
from app.controllers import notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


def get_post_and_validate_or_raise(db: Session, caller_user_id: uuid.UUID, post_id: uuid.UUID) -> models.Post:
    """
    Check that the post exists and the given user is authorized to view it.

    Note: if the user is not authorized (the author blocked the caller user or has been blocked by the caller user),
    a 404 will be returned because they shouldn't even know that the post exists.
    """
    RelationFromCaller = aliased(models.UserRelation)
    RelationToCaller = aliased(models.UserRelation)
    post: Optional[models.Post] = db.query(models.Post) \
        .join(models.User) \
        .join(RelationToCaller,
              (RelationToCaller.from_user_id == models.User.id) & (RelationToCaller.to_user_id == caller_user_id),
              isouter=True) \
        .join(RelationFromCaller,
              (RelationFromCaller.from_user_id == caller_user_id) & (RelationFromCaller.to_user_id == models.User.id),
              isouter=True) \
        .filter(models.Post.id == post_id,
                models.Post.deleted == false(),
                RelationToCaller.relation.is_distinct_from(models.UserRelationType.blocked),
                RelationFromCaller.relation.is_distinct_from(models.UserRelationType.blocked)) \
        .first()
    if post is None:
        raise HTTPException(404, detail="Post not found")
    return post


@router.post("", response_model=schemas.post.Post)
def create_post(
    request: schemas.post.CreatePostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    user_store: UserStore = Depends(UserStore),
    place_store: PlaceStore = Depends(PlaceStore),
    post_store: PostStore = Depends(PostStore)
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
    user_store: UserStore = Depends(UserStore),
    post_store: PostStore = Depends(PostStore)
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
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore),
    post_store: PostStore = Depends(PostStore)
):
    """Like the given post if the user has not already liked the post."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post = get_post_and_validate_or_raise(db, caller_user_id=user.id, post_id=post_id)
    post_store.like_post(user.id, post.id)
    # Notify the user that their post was liked
    prefs = user_store.get_user_preferences(post.user_id)
    if prefs.post_liked_notifications:
        notifications.notify_post_liked(db, post, liked_by=user)
    return {"likes": post.like_count}


@router.delete("/{post_id}/likes", response_model=schemas.post.LikePostResponse)
def unlike_post(
    post_id: uuid.UUID,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore),
    post_store: PostStore = Depends(PostStore)
):
    """Unlike the given post if the user has already liked the post."""
    user: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post = get_post_and_validate_or_raise(db, caller_user_id=user.id, post_id=post_id)
    post_store.unlike_post(user.id, post.id)
    return {"likes": post.like_count}


@router.post("/{post_id}/report", response_model=schemas.base.SimpleResponse)
def report_post(
    post_id: uuid.UUID,
    request: schemas.post.ReportPostRequest,
    firebase_user: FirebaseUser = Depends(get_firebase_user),
    db: Session = Depends(get_db),
    user_store: UserStore = Depends(UserStore),
    post_store: PostStore = Depends(PostStore)
):
    """Report the given post."""
    reported_by: schemas.internal.InternalUser = utils.get_user_from_uid_or_raise(user_store, firebase_user.uid)
    post = get_post_and_validate_or_raise(db, caller_user_id=reported_by.id, post_id=post_id)
    success = post_store.report_post(post.id, reported_by.id, details=request.details)
    return schemas.base.SimpleResponse(success=success)
