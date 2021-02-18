import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import false, or_, case, cast, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import concat, func

from app.controllers import firebase, auth
from app.models.models import User, Post, UserPrefs, Place, Invite, Waitlist
from app.models.request_schemas import UpdateProfileRequest, RectangularRegion, CreateUserRequest
from app.models.response_schemas import UpdateProfileResponse, UserFieldErrors, CreateUserResponse, UserInviteStatus


def username_taken(db: Session, username: str) -> bool:
    """Return whether or not a user (deleted or not) with the given username exists."""
    return db.query(User).filter(User.username_lower == username.lower()).count() > 0


def uid_exists(db: Session, uid: str) -> bool:
    """Return whether or not a user (deleted or not) with the given uid exists."""
    return db.query(User).filter(User.uid == uid).count() > 0


def get_user(db: Session, username: str) -> Optional[User]:
    """Return the user with the given username or None if no such user exists or the user is deleted."""
    return db.query(User).filter(and_(User.username_lower == username.lower(), User.deleted == false())).first()


def get_users_by_phone_numbers(db: Session, phone_numbers: list[str]) -> list[User]:
    """Return the list of users with the given phone numbers."""
    return db.query(User).filter(and_(User.phone_number.in_(phone_numbers), User.deleted == false())).all()


def get_user_by_uid(db: Session, uid: str) -> Optional[User]:
    """Return the user with the given uid or None if no such user exists or the user is deleted."""
    return db.query(User).filter(and_(User.uid == uid, User.deleted == false())).first()


def is_invited(db: Session, uid: str) -> bool:
    phone_number = firebase.get_phone_number_from_uid(uid)
    if phone_number is None:
        return False
    return db.query(Invite).filter(Invite.phone_number == phone_number).count() > 0


def on_waitlist(db: Session, uid: str) -> bool:
    phone_number = firebase.get_phone_number_from_uid(uid)
    if phone_number is None:
        return False
    return db.query(Waitlist).filter(Waitlist.phone_number == phone_number).count() > 0


def invite_user(db: Session, user: User, phone_number: str) -> UserInviteStatus:
    invite = Invite(phone_number=phone_number, invited_by=user.id)
    db.add(invite)
    db.commit()
    return UserInviteStatus(invited=True)


def join_waitlist(db: Session, uid: str):
    phone_number = firebase.get_phone_number_from_uid(uid)
    if phone_number is None:
        raise ValueError("Phone number not found")
    row = Waitlist(phone_number=firebase.get_phone_number_from_uid(uid))
    db.add(row)
    try:
        db.commit()
    except IntegrityError as e:
        # Already on waitlist
        print(e)
        db.rollback()


def create_user(db: Session, uid: str, request: CreateUserRequest, phone_number: Optional[str]) -> CreateUserResponse:
    """Try to create a user with the given information, returning whether the user could be created or not."""
    if not is_invited(db, uid):
        return CreateUserResponse(created=None, error=UserFieldErrors(uid="You aren't invited yet."))
    new_user = User(uid=uid, username=request.username, first_name=request.first_name, last_name=request.last_name,
                    phone_number=phone_number)
    db.add(new_user)
    try:
        db.commit()
        # Initialize user preferences
        prefs = UserPrefs(user_id=new_user.id, post_notifications=False, follow_notifications=True,
                          post_liked_notifications=True)
        db.add(prefs)
        db.commit()
        return CreateUserResponse(created=new_user, error=None)
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
            return CreateUserResponse(created=None, error=UserFieldErrors(other="Unknown error."))


def update_user(db: Session, user: User, request: UpdateProfileRequest) -> UpdateProfileResponse:
    """Update the given user with the given details."""
    if request.username:
        user.username = request.username
    if request.first_name:
        user.first_name = request.first_name
    if request.last_name:
        user.last_name = request.last_name
    if request.profile_picture_url:
        user.profile_picture_url = request.profile_picture_url

    try:
        user.updated_at = datetime.datetime.utcnow()
        db.commit()
        return UpdateProfileResponse(user=user, error=None)
    except IntegrityError as e:
        db.rollback()
        if username_taken(db, request.username):
            return UpdateProfileResponse(user=None, error=UserFieldErrors(username="Username taken."))
        else:
            # Unknown error
            print(e)
            return UpdateProfileResponse(user=None, error=UserFieldErrors(other="Unknown error."))


def update_preferences(db: Session, user: User, request: UserPrefs) -> UserPrefs:
    prefs: UserPrefs = user.preferences
    prefs.follow_notifications = request.follow_notifications
    prefs.post_liked_notifications = request.post_liked_notifications
    prefs.post_notifications = request.post_notifications
    db.commit()
    return UserPrefs(follow_notifications=prefs.follow_notifications,
                     post_liked_notifications=prefs.post_liked_notifications,
                     post_notifications=prefs.post_notifications)


def get_posts(db: Session, user: User) -> list[Post]:
    """Get the user's posts that aren't deleted."""
    return db.query(Post).filter(and_(Post.user_id == user.id, Post.deleted == false())).order_by(
        Post.created_at.desc()).all()


def get_following(user: User) -> list[User]:
    """Return the list of active users the given user is following."""
    return [u for u in user.following if not u.deleted]


def get_feed(db: Session, user: User, before_post_id: Optional[str] = None) -> Optional[list[Post]]:
    """Get the user's feed, returning None if the user is not authorized or if before_post_id is invalid."""
    before_post = None
    if before_post_id is not None:
        before_post = db.query(Post).filter(Post.urlsafe_id == before_post_id).first()
        if before_post is None or not auth.user_can_view_post(user, before_post):
            return None
    following = get_following(user)
    following.append(user)
    following_ids = [u.id for u in following]
    query = db.query(Post).filter(Post.user_id.in_(following_ids), Post.deleted == false())
    if before_post is not None:
        query = query.filter(Post.id < before_post.id)
    return query.order_by(Post.created_at.desc()).limit(50).all()


def get_discover_feed(db: Session) -> list[Post]:
    """Get the user's discover feed."""
    one_week_ago = datetime.datetime.utcnow() - datetime.timedelta(weeks=1)
    # TODO also filter by Post.user_id != user.id, for now it's easier to test without
    return db.query(Post).filter(
        and_(Post.image_url.isnot(None), Post.created_at > one_week_ago, Post.deleted == false())).order_by(
        Post.like_count.desc()).limit(100)


def get_map(db: Session, user: User, bounds: RectangularRegion) -> list[Post]:
    """Get the user's map view, returning up to the 50 most recent posts in the given region."""
    # TODO this is broken, fix
    following_ids = [u.id for u in get_following(user)] + [user.id]
    min_x = bounds.center_long - bounds.span_long / 2
    max_x = bounds.center_long + bounds.span_long / 2
    min_y = bounds.center_lat - bounds.span_lat / 2
    max_y = bounds.center_lat + bounds.span_lat / 2

    min_x = min_x + 360 if min_x < -180 else min_x
    max_x = max_x - 360 if max_x > 180 else max_x

    def _intersects(location_field):
        return func.ST_Intersects(
            func.ST_ShiftLongitude(cast(location_field, Geometry)),
            func.ST_ShiftLongitude(func.ST_MakeEnvelope(min_x, min_y, max_x, max_y, 4326)))

    post_id_query = db.query(Post.id).filter(Post.user_id.in_(following_ids), Post.deleted == false()).join(
        Place).filter(
        case([(Post.custom_location.isnot(None), _intersects(Post.custom_location))],
             else_=_intersects(Place.location))).order_by(Post.created_at.desc()).limit(50)
    return db.query(Post).filter(Post.id.in_(post_id_query)).all()


def search_users(db: Session, query: str) -> list[User]:
    if len(query) < 3:
        # Only search if the query is >= 3 chars
        return []
    # First search usernames
    # TODO this is inefficient, we should move to a real search engine
    return db.query(User).filter(User.deleted == false()).filter(
        or_(User.username.ilike(f"{query}%"), concat(User.first_name, " ", User.last_name).ilike(f"{query}%"))).limit(
        50).all()
