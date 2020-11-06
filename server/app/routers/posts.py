from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.controllers import controller
from app.database import get_db
from app.models import schemas

router = APIRouter()


@router.get("/{post_id}", response_model=schemas.Post)
def get_post(post_id: str, db: Session = Depends(get_db)):
    """Get the given post.

    Args:
        post_id: The post id (maps to urlsafe_id in database).
        db: The database session object. This object is automatically injected by FastAPI.

    Returns:
        The post object.

    Raises:
        HTTPException: If the post could not be found or the called isn't authorized (404) or the caller isn't
        authenticated (401). A 404 is thrown for authorization errors because the caller should not know of
        the existence of the post.
    """
    # TODO(gmekkat): Authenticate caller
    post = controller.get_post(db, post_id)
    if post is None:
        raise HTTPException(404, detail="Post not found")
    return post
