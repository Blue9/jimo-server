from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

import app.controllers.posts
from app.controllers import posts
from app.database import get_db
from app.models import schemas, models
from app.models.request_schemas import CreatePostRequest
from app.models.response_schemas import LikePostResponse
from app.routers import utils
from app.routers.utils import get_email_or_raise, check_can_view_user_else_raise

router = APIRouter()


def get_post_and_validate_or_raise(post_id: str, authorization: Optional[str], db: Session) -> models.Post:
    caller_email = get_email_or_raise(authorization)
    post: models.Post = posts.get_post(db, post_id)
    post_not_found = HTTPException(404, detail="Post not found")
    if post is None or post.deleted:
        raise post_not_found
    check_can_view_user_else_raise(user=post.user, caller_email=caller_email, custom_exception=post_not_found)
    return post


@router.post("/", response_model=schemas.Post)
def create_post(request: CreatePostRequest, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Create a new post.

    Args:
        request: The request to create the post.
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The created post.

    Raises:
        HTTPException: 401 if the user is not authenticated or 400 if there was a problem with the request.
    """
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    try:
        post = app.controllers.posts.create_post(db, user, request)
        fields = schemas.ORMPost.from_orm(post).dict()
        liked = user in post.likes
        return schemas.Post(**fields, liked=liked)
    except ValueError as e:
        print(e)
        raise HTTPException(400, detail=str(e))


@router.get("/{post_id}", response_model=schemas.Post)
def get_post(post_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the given post.

    Args:
        post_id: The post id (maps to urlsafe_id in database).
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The post object.

    Raises:
        HTTPException: If the post could not be found or the called isn't authorized (404) or the caller isn't
        authenticated (401). A 404 is thrown for authorization errors because the caller should not know of
        the existence of the post.
    """
    user: models.User = utils.get_user_from_auth_or_raise(db, authorization)
    post = get_post_and_validate_or_raise(post_id, authorization, db)
    liked = user in post.likes
    fields = schemas.ORMPost.from_orm(post).dict()
    return schemas.Post(**fields, liked=liked)


@router.get("/{post_id}/comments", response_model=List[schemas.Comment])
def get_comments(post_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Get the given post's comments.

    Args:
        post_id: The post id (maps to urlsafe_id in database).
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        A list of comments.

    Raises:
        HTTPException: If the post could not be found or the caller isn't authorized (404) or the caller isn't
        authenticated (401). A 404 is thrown for authorization errors because the caller should not know of
        the existence of the post.
    """
    post = get_post_and_validate_or_raise(post_id, authorization, db)
    return post.comments


@router.post("/{post_id}/likes", response_model=LikePostResponse)
def like_post(post_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Like the given post if the user has not already liked the post.

    Args:
        post_id: The post id (maps to urlsafe_id in database).
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The result of liking the post.

    Raises:
        HTTPException: If the post could not be found or the caller isn't authorized (404) or the caller isn't
        authenticated (401). A 404 is thrown for authorization errors because the caller should not know of
        the existence of the post.
    """
    post = get_post_and_validate_or_raise(post_id, authorization, db)
    user = utils.get_user_from_auth_or_raise(db, authorization)
    posts.like_post(db, user, post)
    return {"likes": post.like_count}


@router.delete("/{post_id}/likes", response_model=LikePostResponse)
def unlike_post(post_id: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """Unlike the given post if the user has already liked the post.

    Args:
        post_id: The post id (maps to urlsafe_id in database).
        authorization: Authorization header. This string is automatically injected by FastAPI.
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The result of unliking the post.

    Raises:
        HTTPException: If the post could not be found or the caller isn't authorized (404) or the caller isn't
        authenticated (401). A 404 is thrown for authorization errors because the caller should not know of
        the existence of the post.
    """
    post = get_post_and_validate_or_raise(post_id, authorization, db)
    user = utils.get_user_from_auth_or_raise(db, authorization)
    posts.unlike_post(db, user, post)
    return {"likes": post.like_count}
