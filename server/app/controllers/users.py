import datetime
import uuid
from typing import Optional, Tuple, Callable

from sqlalchemy import false, or_, and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased, Session
from sqlalchemy.sql.functions import concat

from app import schemas, config
from app.controllers import images, utils
from app.controllers.firebase import FirebaseUser
from app.models import models


def username_taken(db: Session, username: str) -> bool:
    """Return whether or not a user (deleted or not) with the given username exists."""
    return db.query(models.User).filter(models.User.username_lower == username.lower()).count() > 0


def uid_exists(db: Session, uid: str) -> bool:
    """Return whether or not a user (deleted or not) with the given uid exists."""
    return db.query(models.User).filter(models.User.uid == uid).count() > 0


def get_user(db: Session, username: str) -> Optional[models.User]:
    """Return the user with the given username or None if no such user exists or the user is deleted."""
    return db.query(models.User) \
        .filter(and_(models.User.username_lower == username.lower(), models.User.deleted == false())) \
        .first()


def get_users_by_phone_numbers(
    db: Session,
    user: models.User,
    phone_numbers: list[str],
    limit=1000
) -> list[models.User]:
    """Return up to `limit` users with the given phone numbers."""
    return db.query(models.User) \
        .filter(models.User.phone_number.in_(phone_numbers), models.User.deleted == false()) \
        .join(models.UserRelation,
              (models.UserRelation.from_user_id == models.User.id) & (models.UserRelation.to_user_id == user.id),
              isouter=True) \
        .filter(models.UserRelation.relation.is_distinct_from(models.UserRelationType.blocked)) \
        .limit(limit) \
        .all()


def get_user_by_uid(db: Session, uid: str, lock: bool = False) -> Optional[models.User]:
    """Return the user with the given uid or None if no such user exists or the user is deleted."""
    query = db.query(models.User) \
        .filter(and_(models.User.uid == uid, models.User.deleted == false()))
    if lock:
        return query.with_for_update().first()
    else:
        return query.first()


def is_invited(db: Session, firebase_user: FirebaseUser) -> bool:
    phone_number = firebase_user.shared_firebase.get_phone_number_from_uid(firebase_user.uid)
    if phone_number is None:
        return False
    return db.query(models.Invite).filter(models.Invite.phone_number == phone_number).count() > 0


def is_blocked(db: Session, blocked_by_user: models.User, blocked_user: models.User) -> bool:
    query = db.query(models.UserRelation) \
        .filter(models.UserRelation.from_user_id == blocked_by_user.id,
                models.UserRelation.to_user_id == blocked_user.id,
                models.UserRelation.relation == models.UserRelationType.blocked) \
        .exists()
    return db.query(query).scalar()


def on_waitlist(db: Session, firebase_user: FirebaseUser) -> bool:
    phone_number = firebase_user.shared_firebase.get_phone_number_from_uid(firebase_user.uid)
    if phone_number is None:
        return False
    return db.query(models.Waitlist).filter(models.Waitlist.phone_number == phone_number).count() > 0


def invite_user(db: Session, user: models.User, phone_number: str) -> schemas.invite.UserInviteStatus:
    num_used_invites = db.query(models.Invite).filter(models.Invite.invited_by == user.id).count()
    if num_used_invites >= config.INVITES_PER_USER and not user.is_admin:
        return schemas.invite.UserInviteStatus(invited=False, message="Reached invite limit.")
    # Possible race condition if this gets called multiple times for the same user at the same time
    # Rate limiting the endpoint based on the auth header should take care of it, plus the worst case is that someone
    # invites extra users which isn't really a problem
    invite = models.Invite(phone_number=phone_number, invited_by=user.id)
    try:
        db.add(invite)
        db.commit()
    except IntegrityError:
        # User already invited
        return schemas.invite.UserInviteStatus(invited=False, message="User is already invited.")
        pass
    return schemas.invite.UserInviteStatus(invited=True)


def join_waitlist(db: Session, firebase_user: FirebaseUser):
    phone_number = firebase_user.shared_firebase.get_phone_number_from_uid(firebase_user.uid)
    if phone_number is None:
        raise ValueError("Phone number not found")
    row = models.Waitlist(phone_number=phone_number)
    db.add(row)
    try:
        db.commit()
    except IntegrityError as e:
        # Already on waitlist
        print(e)
        db.rollback()


def create_user(db: Session, firebase_user: FirebaseUser, request: schemas.user.CreateUserRequest,
                phone_number: Optional[str]) -> schemas.user.CreateUserResponse:
    """Try to create a user with the given information, returning whether the user could be created or not."""
    if not is_invited(db, firebase_user):
        return schemas.user.CreateUserResponse(created=None,
                                               error=schemas.user.UserFieldErrors(uid="You aren't invited yet."))
    created, error = create_user_ignore_invite_status(db, firebase_user.uid, request.username, request.first_name,
                                                      request.last_name, phone_number)
    return schemas.user.CreateUserResponse(created=created, error=error)


def create_user_ignore_invite_status(
    db: Session,
    uid: str,
    username: str,
    first_name: str,
    last_name: str,
    phone_number: Optional[str] = None
) -> Tuple[Optional[models.User], Optional[schemas.user.UserFieldErrors]]:
    """Create a user ignoring the invite limit."""
    new_user = models.User(uid=uid, username=username, first_name=first_name,
                           last_name=last_name, phone_number=phone_number)
    db.add(new_user)
    try:
        db.commit()
        # Initialize user preferences
        prefs = models.UserPrefs(user_id=new_user.id, post_notifications=False, follow_notifications=True,
                                 post_liked_notifications=True)
        db.add(prefs)
        db.commit()
        return new_user, None
    except IntegrityError as e:
        db.rollback()
        # A user with the same uid or username exists
        if uid_exists(db, uid):
            error = schemas.user.UserFieldErrors(uid="User exists.")
            return None, error
        elif username_taken(db, username):
            error = schemas.user.UserFieldErrors(username="Username taken.")
            return None, error
        else:
            # Unknown error
            print(e)
            return None, schemas.user.UserFieldErrors(other="Unknown error.")


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


def get_posts(
    db: Session,
    caller_user: models.User,
    user: models.User,
    cursor: Optional[uuid.UUID],
    limit: int
) -> list[schemas.post.Post]:
    """Get the user's posts that aren't deleted."""
    user_posts_query = db.query(models.Post, utils.is_post_liked_query(caller_user)) \
        .options(utils.eager_load_post_except_user_options()) \
        .filter(models.Post.user_id == user.id, models.Post.deleted == false())
    if cursor:
        user_posts_query = user_posts_query.filter(models.Post.id < cursor)
    rows = user_posts_query.order_by(models.Post.id.desc()).limit(limit).all()
    user_posts = []
    for post, is_post_liked in rows:
        # ORMPostWithoutUser avoids querying post.user; we already know the user
        fields = schemas.post.ORMPostWithoutUser.from_orm(post).dict()
        user_posts.append(schemas.post.Post(**fields, user=user, liked=is_post_liked))
    return user_posts


def get_following(db: Session, user: models.User) -> list[models.User]:
    """Return the list of active users the given user is following."""
    return db.query(models.User) \
        .join(models.UserRelation, models.UserRelation.to_user_id == models.User.id) \
        .filter(models.UserRelation.from_user_id == user.id,
                models.UserRelation.relation == models.UserRelationType.following,
                models.User.deleted == false()) \
        .all()


def get_feed(db: Session, user: models.User, before_post_id: Optional[uuid.UUID] = None) -> list[schemas.post.Post]:
    """Get the user's feed, returning None if the user is not authorized or if before_post_id is invalid."""
    query = _get_feed_query(db, user)
    if before_post_id:
        query = query.filter(models.Post.id < before_post_id)
    rows = query.order_by(models.Post.id.desc()).limit(50).all()
    return utils.rows_to_posts(rows)


def _get_feed_query(db: Session, user: models.User):
    user_is_following_post_author = db.query(models.UserRelation.to_user_id) \
        .filter(models.UserRelation.to_user_id == models.Post.user_id,
                models.UserRelation.from_user_id == user.id,
                models.UserRelation.relation == models.UserRelationType.following) \
        .exists()
    return db.query(models.Post, utils.is_post_liked_query(user)) \
        .options(utils.eager_load_post_options()) \
        .filter(or_(models.Post.user_id == user.id, user_is_following_post_author), models.Post.deleted == false()) \
        .order_by(models.Post.id.desc())


def get_discover_feed(db: Session, user: models.User) -> list[models.Post]:
    """Get the user's discover feed."""
    one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(weeks=1)
    # TODO also filter by Post.user_id != user.id, for now it's easier to test without
    RelationToCaller = aliased(models.UserRelation)
    RelationFromCaller = aliased(models.UserRelation)
    rows = db.query(models.Post, utils.is_post_liked_query(user)) \
        .options(utils.eager_load_post_options()) \
        .join(models.User) \
        .join(RelationToCaller,
              (RelationToCaller.to_user_id == user.id) & (RelationToCaller.from_user_id == models.User.id),
              isouter=True) \
        .join(RelationFromCaller,
              (RelationFromCaller.from_user_id == user.id) & (RelationFromCaller.to_user_id == models.User.id),
              isouter=True) \
        .filter(RelationToCaller.relation.is_distinct_from(models.UserRelationType.blocked),
                RelationFromCaller.relation.is_distinct_from(models.UserRelationType.blocked),
                models.Post.image_url.isnot(None),
                models.Post.created_at > one_week_ago,
                models.Post.deleted == false()) \
        .order_by(models.Post.like_count.desc()) \
        .limit(500) \
        .all()
    return utils.rows_to_posts(rows)


def _try_add_relation(
    db: Session,
    from_user: models.User,
    to_user: models.User,
    relation: models.UserRelationType,
    before_commit: Callable = None
) -> Optional[models.UserRelationType]:
    """Try to add the relation, returning the existing relation if one already existed."""
    existing_relation: Optional[models.UserRelation] = db.query(models.UserRelation) \
        .filter(models.UserRelation.from_user_id == from_user.id,
                models.UserRelation.to_user_id == to_user.id) \
        .first()
    if existing_relation:
        return existing_relation.relation
    # else:
    relation = models.UserRelation(from_user_id=from_user.id, to_user_id=to_user.id, relation=relation)
    db.add(relation)
    try:
        if before_commit:
            before_commit()
        db.commit()
        return None
    except IntegrityError:
        db.rollback()
        # Most likely we inserted in another request between querying and inserting
        raise ValueError("Could not complete request")


def _remove_relation(
    db: Session,
    from_user: models.User,
    to_user: models.User, relation: models.UserRelationType
) -> bool:
    """Try to remove the relation, returning true if the relation was deleted and false if it didn't exist."""
    existing_relation = db.query(models.UserRelation) \
        .filter(models.UserRelation.from_user_id == from_user.id,
                models.UserRelation.to_user_id == to_user.id,
                models.UserRelation.relation == relation) \
        .delete()
    db.commit()
    return existing_relation > 0


def follow_user(db: Session, from_user: models.User, to_user: models.User) -> schemas.user.FollowUserResponse:
    existing = _try_add_relation(db, from_user, to_user, models.UserRelationType.following)
    if existing == models.UserRelationType.following:
        raise ValueError("Already following user")
    elif existing == models.UserRelationType.blocked:
        raise ValueError("Cannot follow someone you blocked")
    else:
        return schemas.user.FollowUserResponse(followed=True, followers=to_user.follower_count)


def unfollow_user(db: Session, from_user: models.User, to_user: models.User) -> schemas.user.FollowUserResponse:
    unfollowed = _remove_relation(db, from_user, to_user, models.UserRelationType.following)
    if unfollowed:
        return schemas.user.FollowUserResponse(followed=False, followers=to_user.follower_count)
    else:
        raise ValueError("Not following user")


def block_user(db: Session, from_user: models.User, to_user: models.User) -> schemas.base.SimpleResponse:
    """
    Have from_user block to_user.

    Requires that from_user does not already follow or block to_user.
    If from_user (A) blocks to_user (B), make B unfollow A, and remove their likes from each other's posts.
    """

    # TODO: race condition 1: If A and B try to block each other at the same time, they could both go through
    #  and they will be unable to unblock each other.
    # TODO: race condition 2: If B follows A after this transaction starts the follow will go through.
    # TODO: race condition 3: If A/B likes B/A's post after this transaction starts, the inner select stmt won't detect
    #  it, so that like will remain un-deleted.
    def before_commit():
        db.query(models.UserRelation) \
            .filter(models.UserRelation.from_user_id == to_user.id,
                    models.UserRelation.to_user_id == from_user.id,
                    models.UserRelation.relation == models.UserRelationType.following) \
            .delete()
        # Delete to_user's likes of from_user's posts
        db.query(models.PostLike) \
            .filter(models.PostLike.user_id == to_user.id,
                    models.PostLike.post_id.in_(
                        select([models.Post.id]).where(models.Post.user_id == from_user.id))) \
            .delete(synchronize_session=False)
        # Delete from_user's likes of to_user's posts
        db.query(models.PostLike) \
            .filter(models.PostLike.user_id == from_user.id,
                    models.PostLike.post_id.in_(
                        select([models.Post.id]).where(models.Post.user_id == to_user.id))) \
            .delete(synchronize_session=False)

    existing = _try_add_relation(db, from_user, to_user, models.UserRelationType.blocked, before_commit=before_commit)
    if existing == models.UserRelationType.following:
        raise ValueError("Cannot block someone you follow")
    elif existing == models.UserRelationType.blocked:
        raise ValueError("Already blocked")
    else:  # existing is None
        return schemas.base.SimpleResponse(success=True)


def unblock_user(db: Session, from_user: models.User, to_user: models.User) -> schemas.base.SimpleResponse:
    unblocked = _remove_relation(db, from_user, to_user, models.UserRelationType.blocked)
    if unblocked:
        return schemas.base.SimpleResponse(success=True)
    else:
        raise ValueError("Not blocked")


def search_users(db: Session, caller_user: models.User, query: str) -> list[models.User]:
    # First search usernames
    # TODO this is inefficient, we should move to a real search engine
    RelationToCaller = aliased(models.UserRelation)
    db_query = db.query(models.User) \
        .join(RelationToCaller,
              (RelationToCaller.from_user_id == models.User.id) & (RelationToCaller.to_user_id == caller_user.id),
              isouter=True) \
        .filter(RelationToCaller.relation.is_distinct_from(models.UserRelationType.blocked),
                models.User.deleted == false(),
                models.User.is_admin == false()) \
        .filter(or_(models.User.username.ilike(f"{query}%"),
                    concat(models.User.first_name, " ", models.User.last_name).ilike(f"{query}%")))
    if len(query) == 0:
        db_query = db_query.order_by(models.User.follower_count.desc())
    return db_query.limit(50).all()
