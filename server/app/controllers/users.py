from typing import Optional

from sqlalchemy import false, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import concat

from app.controllers import auth
from app.models.models import User, Post, UserPrefs, post_like
from app.models.request_schemas import UpdateUserRequest
from app.models.response_schemas import UpdateUserResponse, UserFieldErrors, CreateUserResponse


def username_taken(db: Session, username: str) -> bool:
    """Return whether or not a user with the given username exists."""
    return db.query(User).filter(User.username_lower == username.lower()).count() > 0


def email_taken(db: Session, email: str) -> bool:
    """Return whether or not a user with the given email exists."""
    return db.query(User).filter(User.email == email).count() > 0


def get_user(db: Session, username: str) -> Optional[User]:
    """Return the user with the given username or None if no such user exists."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Return the user with the given email or None if no such user exists."""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, email: str, username: str, first_name: str, last_name: str) -> CreateUserResponse:
    """Try to create a user with the given information, returning whether the user could be created or not."""
    new_user = User(email=email, username=username, first_name=first_name, last_name=last_name)
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # A user with the same username or email exists
        if email_taken(db, email):
            error = UserFieldErrors(email="Profile already exists.")
            return CreateUserResponse(created=None, error=error)
        elif username_taken(db, username):
            error = UserFieldErrors(username="Username taken.")
            return CreateUserResponse(created=None, error=error)
        else:
            # Unknown error
            print(e)
            return CreateUserResponse(created=None, error=None)
    # Initialize user preferences
    prefs = UserPrefs(user_id=new_user.id, post_notifications=False, follow_notifications=True,
                      post_liked_notifications=True)
    db.add(prefs)
    db.commit()
    return CreateUserResponse(created=new_user, error=None)


def update_user(db: Session, user: User, request: UpdateUserRequest) -> UpdateUserResponse:
    """Update the given user with the given details."""
    errors = UserFieldErrors()

    def attempt_update(column_name, message_if_fail):
        try:
            setattr(user, column_name, getattr(request, column_name))
            db.commit()
        except IntegrityError:
            db.rollback()
            setattr(errors, column_name, message_if_fail)

    if request.username and len(request.username) > 0:
        attempt_update("username", "Username taken.")
    if request.first_name:
        attempt_update("first_name", "Failed to update first name")
    if request.last_name:
        attempt_update("last_name", "Failed to update last name")
    if request.private_account is not None:
        attempt_update("private_account", "Failed to update private account settings")

    user_pref_errors = update_user_prefs(db, user, request)
    if user_pref_errors:
        errors.post_notifications = user_pref_errors.post_notifications
        errors.follow_notifications = user_pref_errors.follow_notifications
        errors.post_liked_notifications = user_pref_errors.post_liked_notifications

    if len(errors.dict(exclude_none=True)):
        return UpdateUserResponse(user=user, errors=errors)
    else:
        return UpdateUserResponse(user=user)


def update_user_prefs(db: Session, user: User, request: UpdateUserRequest) -> Optional[UserFieldErrors]:
    errors = UserFieldErrors()
    user_prefs = db.query(UserPrefs).filter(UserPrefs.user_id == user.id).first()

    def attempt_update(column_name, message_if_fail):
        if user_prefs is None:
            # Something is wrong, the user was not created properly
            # This state should never happen
            setattr(errors, column_name, message_if_fail)
            return
        try:
            setattr(user_prefs, column_name, getattr(request, column_name))
            db.commit()
        except IntegrityError:
            db.rollback()
            setattr(errors, column_name, message_if_fail)

    if request.follow_notifications is not None:
        attempt_update("follow_notifications", "Failed to update notification settings")
    if request.post_liked_notifications is not None:
        attempt_update("post_liked_notifications", "Failed to update notification settings")

    if len(errors.dict(exclude_none=True)):
        return errors
    else:
        return None


def get_feed(db: Session, user: User, before_post_id: Optional[str] = None) -> Optional[list[Post]]:
    """Get the user's feed, returning None if the user is not authorized or if before_post_id is invalid."""
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


def search_users(db: Session, query: str) -> list[User]:
    if len(query) < 3:
        # Only search if the query is >= 3 chars
        return []
    # First search usernames
    return db.query(User).filter(
        or_(User.username.ilike(f"{query}%"), concat(User.first_name, " ", User.last_name).ilike(f"{query}%"))).limit(
        50).all()
