import datetime
from typing import Optional

from sqlalchemy import false, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import concat

from app import schemas, config
from app.controllers import firebase, auth, images
from app.models import models


def username_taken(db: Session, username: str) -> bool:
    """Return whether or not a user (deleted or not) with the given username exists."""
    return db.query(models.User).filter(models.User.username_lower == username.lower()).count() > 0


def uid_exists(db: Session, uid: str) -> bool:
    """Return whether or not a user (deleted or not) with the given uid exists."""
    return db.query(models.User).filter(models.User.uid == uid).count() > 0


def get_user(db: Session, username: str) -> Optional[models.User]:
    """Return the user with the given username or None if no such user exists or the user is deleted."""
    return db.query(models.User).filter(
        and_(models.User.username_lower == username.lower(), models.User.deleted == false())).first()


def get_users_by_phone_numbers(db: Session, phone_numbers: list[str]) -> list[models.User]:
    """Return the list of users with the given phone numbers."""
    return db.query(models.User).filter(
        and_(models.User.phone_number.in_(phone_numbers), models.User.deleted == false())).all()


def get_user_by_uid(db: Session, uid: str) -> Optional[models.User]:
    """Return the user with the given uid or None if no such user exists or the user is deleted."""
    return db.query(models.User).filter(and_(models.User.uid == uid, models.User.deleted == false())).first()


def is_invited(db: Session, uid: str) -> bool:
    phone_number = firebase.get_phone_number_from_uid(uid)
    if phone_number is None:
        return False
    return db.query(models.Invite).filter(models.Invite.phone_number == phone_number).count() > 0


def on_waitlist(db: Session, uid: str) -> bool:
    phone_number = firebase.get_phone_number_from_uid(uid)
    if phone_number is None:
        return False
    return db.query(models.Waitlist).filter(models.Waitlist.phone_number == phone_number).count() > 0


def invite_user(db: Session, user: models.User, phone_number: str) -> schemas.invite.UserInviteStatus:
    num_used_invites = db.query(models.Invite).filter(models.Invite.invited_by == user.id).count()
    if num_used_invites >= config.invites_per_user:
        return schemas.invite.UserInviteStatus(invited=False, message="Reached invite limit.")
    # Possible race condition if this gets called multiple times for the same user at the same time
    # Rate limiting the endpoint should take care of it, plus the worst case is that someone invites extra users
    # which isn't really a problem
    invite = models.Invite(phone_number=phone_number, invited_by=user.id)
    try:
        db.add(invite)
        db.commit()
    except IntegrityError:
        # User already invited
        return schemas.invite.UserInviteStatus(invited=False, message="User is already invited.")
        pass
    return schemas.invite.UserInviteStatus(invited=True)


def join_waitlist(db: Session, uid: str):
    phone_number = firebase.get_phone_number_from_uid(uid)
    if phone_number is None:
        raise ValueError("Phone number not found")
    row = models.Waitlist(phone_number=firebase.get_phone_number_from_uid(uid))
    db.add(row)
    try:
        db.commit()
    except IntegrityError as e:
        # Already on waitlist
        print(e)
        db.rollback()


def create_user(db: Session, uid: str, request: schemas.user.CreateUserRequest,
                phone_number: Optional[str]) -> schemas.user.CreateUserResponse:
    """Try to create a user with the given information, returning whether the user could be created or not."""
    if not is_invited(db, uid):
        return schemas.user.CreateUserResponse(created=None,
                                               error=schemas.user.UserFieldErrors(uid="You aren't invited yet."))
    new_user = models.User(uid=uid, username=request.username, first_name=request.first_name,
                           last_name=request.last_name, phone_number=phone_number)
    db.add(new_user)
    try:
        db.commit()
        # Initialize user preferences
        prefs = models.UserPrefs(user_id=new_user.id, post_notifications=False, follow_notifications=True,
                                 post_liked_notifications=True)
        db.add(prefs)
        db.commit()
        return schemas.user.CreateUserResponse(created=new_user, error=None)
    except IntegrityError as e:
        db.rollback()
        # A user with the same uid or username exists
        if uid_exists(db, uid):
            error = schemas.user.UserFieldErrors(uid="User exists.")
            return schemas.user.CreateUserResponse(created=None, error=error)
        elif username_taken(db, request.username):
            error = schemas.user.UserFieldErrors(username="Username taken.")
            return schemas.user.CreateUserResponse(created=None, error=error)
        else:
            # Unknown error
            print(e)
            return schemas.user.CreateUserResponse(created=None,
                                                   error=schemas.user.UserFieldErrors(other="Unknown error."))


def update_user(db: Session, user: models.User,
                request: schemas.user.UpdateProfileRequest) -> schemas.user.UpdateProfileResponse:
    """Update the given user with the given details."""
    if request.profile_picture_id:
        image = images.maybe_get_image_with_lock(db, user, request.profile_picture_id)
        if image is None:
            db.rollback()
            return schemas.user.UpdateProfileResponse(user=None,
                                                      error=schemas.user.UserFieldErrors(other="Invalid image"))
        image.used = True
        user.profile_picture_id = image.id
    if request.username:
        user.username = request.username
    if request.first_name:
        user.first_name = request.first_name
    if request.last_name:
        user.last_name = request.last_name

    try:
        db.commit()
        return schemas.user.UpdateProfileResponse(user=user, error=None)
    except IntegrityError as e:
        db.rollback()
        if username_taken(db, request.username):
            return schemas.user.UpdateProfileResponse(user=None,
                                                      error=schemas.user.UserFieldErrors(username="Username taken."))
        else:
            # Unknown error
            print(e)
            return schemas.user.UpdateProfileResponse(user=None,
                                                      error=schemas.user.UserFieldErrors(other="Unknown error."))


def update_preferences(db: Session, user: models.User, request: models.UserPrefs) -> models.UserPrefs:
    prefs: models.UserPrefs = user.preferences
    prefs.follow_notifications = request.follow_notifications
    prefs.post_liked_notifications = request.post_liked_notifications
    prefs.post_notifications = request.post_notifications
    db.commit()
    return models.UserPrefs(follow_notifications=prefs.follow_notifications,
                            post_liked_notifications=prefs.post_liked_notifications,
                            post_notifications=prefs.post_notifications)


def get_posts(db: Session, user: models.User) -> list[models.Post]:
    """Get the user's posts that aren't deleted."""
    return db.query(models.Post).filter(and_(models.Post.user_id == user.id, models.Post.deleted == false())).order_by(
        models.Post.created_at.desc()).all()


def get_following(user: models.User) -> list[models.User]:
    """Return the list of active users the given user is following."""
    return [u for u in user.following if not u.deleted]


def get_feed(db: Session, user: models.User, before_post_id: Optional[str] = None) -> Optional[list[models.Post]]:
    """Get the user's feed, returning None if the user is not authorized or if before_post_id is invalid."""
    before_post = None
    if before_post_id is not None:
        before_post = db.query(models.Post).filter(models.Post.urlsafe_id == before_post_id).first()
        if before_post is None or not auth.user_can_view_post(user, before_post):
            return None
    following = get_following(user)
    following.append(user)
    following_ids = [u.id for u in following]
    query = db.query(models.Post).filter(models.Post.user_id.in_(following_ids), models.Post.deleted == false())
    if before_post is not None:
        query = query.filter(models.Post.id < before_post.id)
    return query.order_by(models.Post.created_at.desc()).limit(50).all()


def get_discover_feed(db: Session) -> list[models.Post]:
    """Get the user's discover feed."""
    one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(weeks=1)
    # TODO also filter by Post.user_id != user.id, for now it's easier to test without
    return db.query(models.Post) \
        .filter(models.Post.image_url.isnot(None), models.Post.created_at > one_week_ago,
                models.Post.deleted == false()) \
        .order_by(models.Post.like_count.desc()) \
        .limit(100) \
        .all()


def follow_user(db: Session, from_user: models.User, to_user: models.User) -> schemas.user.FollowUserResponse:
    from_user.following.append(to_user)
    db.commit()
    return schemas.user.FollowUserResponse(followed=True, followers=len(to_user.followers))


def unfollow_user(db: Session, from_user: models.User, to_user: models.User) -> schemas.user.FollowUserResponse:
    unfollow = models.follow.delete().where(
        and_(models.follow.c.from_user_id == from_user.id, models.follow.c.to_user_id == to_user.id))
    db.execute(unfollow)
    db.commit()
    return schemas.user.FollowUserResponse(followed=False, followers=len(to_user.followers))


def search_users(db: Session, query: str) -> list[models.User]:
    if len(query) < 3:
        # Only search if the query is >= 3 chars
        return []
    # First search usernames
    # TODO this is inefficient, we should move to a real search engine
    return db.query(models.User).filter(models.User.deleted == false()).filter(
        or_(models.User.username.ilike(f"{query}%"),
            concat(models.User.first_name, " ", models.User.last_name).ilike(f"{query}%"))).limit(50).all()
