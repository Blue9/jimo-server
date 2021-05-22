import uuid
from typing import Optional, Tuple

from sqlalchemy.sql.functions import concat

from app import schemas
from app.controllers import images
from app.db.database import get_db
from app.models import models
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased


class UserStore:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    # Scalar queries

    def is_username_taken(self, username: str) -> bool:
        """Return whether or not a user (deleted or not) with the given username exists."""
        query = self.db.query(models.User).filter(models.User.username_lower == username.lower()).exists()
        return self.db.query(query).scalar()

    def is_uid_taken(self, uid: str) -> bool:
        """Return whether or not a user (deleted or not) with the given uid exists."""
        query = self.db.query(models.User).filter(models.User.uid == uid).exists()
        return self.db.query(query).scalar()

    # Queries

    def get_user_by_uid(self, uid: str) -> Optional[schemas.internal.InternalUser]:
        """Return the user with the given uid or None if no such user exists or the user is deleted."""
        user = self.db.query(models.User) \
            .filter(models.User.uid == uid,
                    ~models.User.deleted) \
            .first()
        return schemas.internal.InternalUser.from_orm(user) if user else None

    def get_user_by_username(self, username: str) -> Optional[schemas.internal.InternalUser]:
        """Return the user with the given username or None if no such user exists or the user is deleted."""
        user = self.db.query(models.User) \
            .filter(models.User.username_lower == username.lower(),
                    ~models.User.deleted) \
            .first()
        return schemas.internal.InternalUser.from_orm(user) if user else None

    def get_users_by_phone_number(
        self,
        user_id: uuid.UUID,
        phone_numbers: list[str],
        limit: int = 1000
    ) -> list[schemas.user.PublicUser]:
        """Return up to `limit` users with the given phone numbers."""
        blocked_subquery = select(models.UserRelation.from_user_id).select_from(models.UserRelation).where(
            models.UserRelation.to_user_id == user_id,
            models.UserRelation.relation == models.UserRelationType.blocked)
        users = self.db.query(models.User) \
            .filter(models.User.phone_number.in_(phone_numbers),
                    models.User.id.notin_(blocked_subquery),
                    ~models.User.deleted) \
            .limit(limit) \
            .all()
        return [schemas.user.PublicUser.from_orm(user) for user in users]

    def search_users(self, caller_user_id: uuid.UUID, query: str) -> list[schemas.user.PublicUser]:
        # First search usernames
        # TODO this is inefficient, we should move to a real search engine
        relation_to_user = aliased(models.UserRelation)
        query = query.replace("\\", "\\\\").replace("_", "\\_").replace("%", "\\%")
        db_query = self.db.query(models.User) \
            .join(relation_to_user,
                  (relation_to_user.from_user_id == models.User.id) & (relation_to_user.to_user_id == caller_user_id),
                  isouter=True) \
            .filter(relation_to_user.relation.is_distinct_from(models.UserRelationType.blocked),
                    ~models.User.deleted,
                    ~models.User.is_admin) \
            .filter(models.User.username.ilike(f"{query}%")
                    | concat(models.User.first_name, " ", models.User.last_name).ilike(f"{query}%"))
        if len(query) == 0:
            db_query = db_query.order_by(models.User.follower_count.desc())
        users = db_query.limit(50).all()
        return [schemas.user.PublicUser.from_orm(user) for user in users]

    def get_user_preferences(self, user_id: uuid.UUID) -> schemas.user.UserPrefs:
        prefs = self.db.query(models.UserPrefs).filter(models.UserPrefs.user_id == user_id).first()
        return (schemas.user.UserPrefs.from_orm(prefs) if prefs else
                schemas.user.UserPrefs(post_notifications=False, follow_notifications=False,
                                       post_liked_notifications=False))

    # Operations

    def create_user(
        self,
        uid: str,
        username: str,
        first_name: str,
        last_name: str,
        phone_number: Optional[str] = None
    ) -> Tuple[Optional[schemas.internal.InternalUser], Optional[schemas.user.UserFieldErrors]]:
        """Create a new user with the given details."""
        new_user = models.User(
            uid=uid, username=username, first_name=first_name, last_name=last_name, phone_number=phone_number)
        self.db.add(new_user)
        try:
            self.db.commit()
            # Initialize user preferences
            prefs = models.UserPrefs(user_id=new_user.id, post_notifications=False, follow_notifications=True,
                                     post_liked_notifications=True)
            self.db.add(prefs)
            self.db.commit()
            return schemas.internal.InternalUser.from_orm(new_user), None
        except IntegrityError as e:
            self.db.rollback()
            # A user with the same uid or username exists
            if self.is_uid_taken(uid):
                error = schemas.user.UserFieldErrors(uid="User exists.")
                return None, error
            elif self.is_username_taken(username):
                error = schemas.user.UserFieldErrors(username="Username taken.")
                return None, error
            else:
                # Unknown error
                print(e)
                return None, schemas.user.UserFieldErrors(other="Unknown error.")

    def update_user(
        self,
        user_id: uuid.UUID,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        profile_picture_id: Optional[uuid.UUID] = None
    ) -> Tuple[Optional[schemas.internal.InternalUser], Optional[schemas.user.UserFieldErrors]]:
        """Update the given user with the given details."""
        user = self.db.query(models.User).filter(models.User.id == user_id, ~models.User.deleted).first()
        if user is None:
            return None, schemas.user.UserFieldErrors(uid="User not found")
        if profile_picture_id:
            image = images.maybe_get_image_with_lock(self.db, user.id, profile_picture_id)
            if image is None:
                self.db.rollback()
                return None, schemas.user.UserFieldErrors(other="Invalid image")
            image.used = True
            user.profile_picture_id = image.id
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        try:
            self.db.commit()
            return schemas.internal.InternalUser.from_orm(user), None
        except IntegrityError as e:
            self.db.rollback()
            if username and self.is_username_taken(username):
                return None, schemas.user.UserFieldErrors(username="Username taken.")
            else:
                # Unknown error
                print(e)
                return None, schemas.user.UserFieldErrors(other="Unknown error.")

    def update_preferences(self, user_id: uuid.UUID, request: schemas.user.UserPrefs) -> schemas.user.UserPrefs:
        """Update the given user's preferences."""
        prefs: models.UserPrefs = self.db.query(models.UserPrefs).filter(models.UserPrefs.user_id == user_id).first()
        if prefs is None:
            return request
        prefs.follow_notifications = request.follow_notifications
        prefs.post_liked_notifications = request.post_liked_notifications
        prefs.post_notifications = request.post_notifications
        self.db.commit()
        return schemas.user.UserPrefs.from_orm(prefs)
