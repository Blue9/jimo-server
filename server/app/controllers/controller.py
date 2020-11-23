from typing import Optional

from sqlalchemy import false
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.controllers import auth
from app.models.models import User, Post, Comment, UserPrefs
from app.models.request_schemas import UpdateUserRequest
from app.models.response_schemas import UpdateUserResponse, UpdateUserErrors


def get_user(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def create_user(db: Session, email: str, username: str, first_name: str, last_name: str) -> bool:
    """Try to create a user with the given information, returning whether the user could be created or not."""
    new_user = User(email=email, username=username, first_name=first_name, last_name=last_name)
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        # A user with the same username or email exists
        return False
    # Initialize user preferences
    try:
        prefs = UserPrefs(user_id=new_user.id, post_notifications=False, follow_notifications=True,
                          post_liked_notifications=True)
        db.add(prefs)
        db.commit()
    except IntegrityError:
        pass  # It's fine
    return True


def update_user(db: Session, user: User, request: UpdateUserRequest) -> UpdateUserResponse:
    errors = UpdateUserErrors()

    def attempt_update(column_name, message_if_fail):
        try:
            setattr(user, column_name, getattr(request, column_name))
            db.commit()
        except IntegrityError:
            setattr(errors, column_name, message_if_fail)

    if request.username and len(request.username) > 0:
        if not request.username[0].isalpha():
            errors.username = "First character of username must be a letter"
        elif not request.username.isalnum():
            errors.username = "Username can only contain letters and numbers"
        elif len(request.username) < 3:
            errors.username = "Username must be at least 3 characters"
        else:
            attempt_update("username", "Username already exists")
    if request.first_name:
        attempt_update("first_name", "Failed to update first name")
    if request.last_name:
        attempt_update("last_name", "Failed to update last name")
    if request.private_account is not None:
        attempt_update("private_account", "Failed to update private account settings")
    if request.post_notifications is not None:
        attempt_update("post_notifications", "Failed to update notification settings")
    if request.follow_notifications is not None:
        attempt_update("follow_notifications", "Failed to update notification settings")
    if request.post_liked_notifications is not None:
        attempt_update("post_liked_notifications", "Failed to update notification settings")

    if len(errors.dict(exclude_none=True)):
        return UpdateUserResponse(errors=errors)
    else:
        return UpdateUserResponse(user=user)


def get_feed(db: Session, user: User, before_post_id: Optional[str] = None) -> Optional[list[Post]]:
    before_post = None
    if before_post_id is not None:
        before_post = db.query(Post).filter(Post.urlsafe_id == before_post_id, Post.deleted == false()).first()
        if before_post is None or not auth.user_can_view_post(user, before_post):
            return None
    following_ids = [u.id for u in user.following]
    following_ids.append(user.id)
    query = db.query(Post).filter(Post.user_id.in_(following_ids), Post.deleted == false())
    if before_post is not None:
        query = query.filter(Post.id > before_post.id)
    return query.order_by(Post.created_at.desc()).limit(50).all()


def get_post(db: Session, post_id: str):
    return db.query(Post).filter(Post.urlsafe_id == post_id).first()


def get_comments(db: Session, post_id: str) -> Optional[list[Comment]]:
    post = db.query(Post).filter(Post.urlsafe_id == post_id).first()
    if not post:
        return None
    return post.comments
