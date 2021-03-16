from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

from app import schemas
from app.api import utils
from app.controllers import posts, notifications
from app.controllers.firebase import FirebaseUser, get_firebase_user
from app.db.database import get_db
from app.models import models

router = APIRouter()


def get_post_and_validate_or_raise(post_id: str, db: Session) -> models.Post:
    post: Optional[models.Post] = posts.get_post(db, post_id)
    if post is None:
        raise HTTPException(404, detail="Post not found")
    return post


@router.post("", response_model=schemas.post.Post)
def create_post(request: schemas.post.CreatePostRequest, firebase_user: FirebaseUser = Depends(get_firebase_user),
                db: Session = Depends(get_db)):
    """Create a new post.

    Args:
        request: The request to create the post.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The created post.

    Raises:
        HTTPException: 401 if the user is not authenticated or 400 if there was a problem with the request.
    """
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    try:
        post = posts.create_post(db, user, request)
        fields = schemas.post.ORMPost.from_orm(post).dict()
        liked = user in post.likes
        return schemas.post.Post(**fields, liked=liked)
    except ValueError as e:
        print(e)
        raise HTTPException(400, detail=str(e))


@router.delete("/{post_id}", response_model=schemas.post.DeletePostResponse)
def delete_post(
        post_id: str,
        background_tasks: BackgroundTasks,
        firebase_user: FirebaseUser = Depends(get_firebase_user),
        db: Session = Depends(get_db),
):
    """Delete the given post.

    Args:
        post_id: The post id (maps to external_id in database).
        background_tasks: BackgroundTasks object.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The post object.

    Raises:
        Whether the post could be deleted or not.
    """
    user: models.User = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    post: Optional[models.Post] = posts.get_post(db, post_id)
    if post is not None and post.user == user:
        post.deleted = True
        db.commit()
        if post.image:
            background_tasks.add_task(firebase_user.shared_firebase.make_image_private, post.image.firebase_blob_name)
        return schemas.post.DeletePostResponse(deleted=True)
    return schemas.post.DeletePostResponse(deleted=False)


@router.post("/{post_id}/likes", response_model=schemas.post.LikePostResponse)
def like_post(
        post_id: str,
        background_tasks: BackgroundTasks,
        firebase_user: FirebaseUser = Depends(get_firebase_user),
        db: Session = Depends(get_db)
):
    """Like the given post if the user has not already liked the post.

    Args:
        post_id: The post id (maps to external_id in database).
        background_tasks: BackgroundTasks object.
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The result of liking the post.

    Raises:
        HTTPException: If the post could not be found or the caller isn't authorized (404) or the caller isn't
        authenticated (401). A 404 is thrown for authorization errors because the caller should not know of
        the existence of the post.
    """
    post = get_post_and_validate_or_raise(post_id, db=db)
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    posts.like_post(db, user, post)
    # Notify the user that their post was liked
    background_tasks.add_task(notifications.notify_post_liked_if_enabled, db, post, liked_by=user)
    return {"likes": post.like_count}


@router.delete("/{post_id}/likes", response_model=schemas.post.LikePostResponse)
def unlike_post(post_id: str, firebase_user: FirebaseUser = Depends(get_firebase_user), db: Session = Depends(get_db)):
    """Unlike the given post if the user has already liked the post.

    Args:
        post_id: The post id (maps to external_id in database).
        firebase_user: Firebase user from auth header.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The result of unliking the post.

    Raises:
        HTTPException: If the post could not be found or the caller isn't authorized (404) or the caller isn't
        authenticated (401). A 404 is thrown for authorization errors because the caller should not know of
        the existence of the post.
    """
    post = get_post_and_validate_or_raise(post_id, db=db)
    user = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    posts.unlike_post(db, user, post)
    return {"likes": post.like_count}


@router.post("/{post_id}/report", response_model=schemas.base.SimpleResponse)
def report_post(post_id: str, request: schemas.post.ReportPostRequest,
                firebase_user: FirebaseUser = Depends(get_firebase_user),
                db: Session = Depends(get_db)):
    """Report the given post."""
    post = get_post_and_validate_or_raise(post_id, db=db)
    reported_by = utils.get_user_from_uid_or_raise(db, firebase_user.uid)
    success = posts.report_post(db, post, reported_by, details=request.details)
    # TODO: if successful, notify ourselves (e.g, email)
    return schemas.base.SimpleResponse(success=success)
