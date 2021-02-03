from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import false, or_, case, cast, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import concat, func

from app.controllers import auth
from app.models.models import User, Post, UserPrefs, Place, Invite, Waitlist
from app.models.request_schemas import UpdateUserRequest, RectangularRegion, CreateUserRequest
from app.models.response_schemas import UpdateUserResponse, UserFieldErrors, CreateUserResponse, UserInviteStatus


def username_taken(db: Session, username: str) -> bool:
    """Return whether or not a user with the given username exists."""
    return db.query(User).filter(User.username_lower == username.lower()).count() > 0


def uid_exists(db: Session, uid: str) -> bool:
    return db.query(User).filter(User.uid == uid).count() > 0


def get_user(db: Session, username: str) -> Optional[User]:
    """Return the user with the given username or None if no such user exists."""
    return db.query(User).filter(User.username == username).first()


def get_user_by_uid(db: Session, uid: str) -> Optional[User]:
    """Return the user with the given uid or None if no such user exists."""
    return db.query(User).filter(User.uid == uid).first()


def is_invited(db: Session, uid: str) -> bool:
    phone_number = auth.get_phone_number_from_uid(uid)
    if phone_number is None:
        return False
    return db.query(Invite).filter(Invite.phone_number == phone_number).count() > 0


def on_waitlist(db: Session, uid: str) -> bool:
    phone_number = auth.get_phone_number_from_uid(uid)
    if phone_number is None:
        return False
    return db.query(Waitlist).filter(Waitlist.phone_number == phone_number).count() > 0


def invite_user(db: Session, user: User, phone_number: str) -> UserInviteStatus:
    invite = Invite(phone_number=phone_number, invited_by=user.id)
    db.add(invite)
    try:
        db.commit()
        return UserInviteStatus(invited=True)
    except IntegrityError as e:
        print(e)
        db.rollback()
        return UserInviteStatus(invited=False)


def join_waitlist(db: Session, uid: str):
    phone_number = auth.get_phone_number_from_uid(uid)
    if phone_number is None:
        raise ValueError("Phone number not found")
    row = Waitlist(phone_number=auth.get_phone_number_from_uid(uid))
    db.add(row)
    try:
        db.commit()
    except IntegrityError as e:
        # Already on waitlist
        print(e)
        db.rollback()


def create_user(db: Session, uid: str, request: CreateUserRequest) -> CreateUserResponse:
    """Try to create a user with the given information, returning whether the user could be created or not."""
    if not is_invited(db, uid):
        return CreateUserResponse(created=None, error=UserFieldErrors(uid="You aren't invited yet."))
    new_user = User(uid=uid, username=request.username, first_name=request.first_name, last_name=request.last_name)
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # A user with the same uid or username exists
        if uid_exists(db, uid):
            error = UserFieldErrors(uid="User exists.")
            return CreateUserResponse(created=None, error=error)
        elif username_taken(db, request.username):
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


def get_posts(db: Session, user: User) -> list[Post]:
    """Get the user's posts that aren't deleted."""
    return db.query(Post).filter(and_(Post.user_id == user.id, Post.deleted == False)).order_by(
        Post.created_at.desc()).all()


def get_map(db: Session, user: User, bounds: RectangularRegion) -> list[Post]:
    """Get the user's map view, returning up to the 50 most recent posts in the given region."""
    # TODO this is broken, fix
    following_ids = [u.id for u in user.following] + [user.id]
    min_x = bounds.center_long - bounds.span_long / 2
    max_x = bounds.center_long + bounds.span_long / 2
    min_y = bounds.center_lat - bounds.span_lat / 2
    max_y = bounds.center_lat + bounds.span_lat / 2

    min_x = min_x + 360 if min_x < -180 else min_x
    max_x = max_x - 360 if max_x > 180 else max_x
    post_id_query = db.query(Post.id).filter(Post.user_id.in_(following_ids), Post.deleted == false()).join(
        Place).filter(
        case([(Post.custom_location.isnot(None), _intersects(Post.custom_location, min_x, min_y, max_x, max_y))],
             else_=_intersects(Place.location, min_x, min_y, max_x, max_y))).order_by(Post.created_at.desc()).limit(50)
    return db.query(Post).filter(Post.id.in_(post_id_query)).all()


def _intersects(location_field, min_x, min_y, max_x, max_y):
    return func.ST_Intersects(
        func.ST_ShiftLongitude(cast(location_field, Geometry)),
        func.ST_ShiftLongitude(func.ST_MakeEnvelope(min_x, min_y, max_x, max_y, 4326)))


def search_users(db: Session, query: str) -> list[User]:
    if len(query) < 3:
        # Only search if the query is >= 3 chars
        return []
    # First search usernames
    return db.query(User).filter(
        or_(User.username.ilike(f"{query}%"), concat(User.first_name, " ", User.last_name).ilike(f"{query}%"))).limit(
        50).all()
