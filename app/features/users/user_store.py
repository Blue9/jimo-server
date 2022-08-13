from typing import Optional, Tuple, Sequence

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.complex_queries import get_suggested_users_query
from app.core.database.helpers import maybe_get_image_with_lock
from app.core.database.models import UserRow, UserPrefsRow
from app.core.internal import InternalUser
from app.core.types import PhoneNumber, UserId, ImageId
from app.features.users.entities import UserPrefs, SuggestedUserIdItem, UserFieldErrors
from app.features.users.user_prefs_query import UserPrefsQuery
from app.features.users.user_query import UserQuery


class UserStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    # Scalar query
    async def is_username_taken(self, username: str) -> bool:
        """Return whether or not a user (deleted or not) with the given username exists."""
        return await UserQuery().username(username).execute_exists(self.db)

    async def is_uid_taken(self, uid: str) -> bool:
        """Return whether or not a user (deleted or not) with the given uid exists."""
        return await UserQuery().uid(uid).execute_exists(self.db)

    # Queries
    async def get_user(self, user_id: UserId, include_deleted: bool = False) -> Optional[InternalUser]:
        user = await UserQuery().user_id(user_id).execute_one(self.db, include_deleted=include_deleted)
        return InternalUser.from_orm(user) if user else None

    async def get_users(self, user_ids: list[UserId]) -> dict[UserId, InternalUser]:
        users = await UserQuery().user_id_in(user_ids).execute_many(self.db)
        return {user.id: InternalUser.from_orm(user) for user in users}

    async def get_user_by_uid(self, uid: str, include_deleted: bool = False) -> Optional[InternalUser]:
        """Return the user with the given uid if one exists."""
        user = await UserQuery().uid(uid).execute_one(self.db, include_deleted=include_deleted)
        return InternalUser.from_orm(user) if user else None

    async def get_user_by_username(self, username: str) -> Optional[InternalUser]:
        """Return the user with the given username or None if no such user exists or the user is deleted."""
        user = await UserQuery().username(username).execute_one(self.db)
        return InternalUser.from_orm(user) if user else None

    async def get_users_by_phone_number(self, phone_numbers: Sequence[PhoneNumber], limit: int = 100) -> list[UserId]:
        """Return up to `limit` users with the given phone numbers."""
        return (
            await UserQuery(query_entity=UserRow.id)
            .phone_number_in(phone_numbers)
            .is_searchable_by_phone_number()
            .limit(limit)
            .execute_many(self.db)
        )

    async def search_users(self, query: str) -> list[UserId]:
        return (
            await UserQuery()
            .filter_by_keyword(query)
            .order_by(UserRow.follower_count.desc())
            .limit(50)
            .execute_many(self.db)
        )

    async def get_user_preferences(self, user_id: UserId) -> UserPrefs:
        prefs = await UserPrefsQuery().user_id(user_id).execute_one(self.db)
        return (
            UserPrefs.from_orm(prefs)
            if prefs
            else UserPrefs(
                follow_notifications=False,
                comment_notifications=False,
                post_liked_notifications=False,
                comment_liked_notifications=False,
                searchable_by_phone_number=False,
            )
        )

    async def get_featured_users(self) -> list[UserId]:
        """Return all featured users."""
        return await UserQuery(query_entity=UserRow.id).is_featured().execute_many(self.db)

    async def get_suggested_users(self, user_id: UserId, limit: int = 25) -> list[SuggestedUserIdItem]:
        """Get the list of suggested users for the given user_id."""
        query = get_suggested_users_query(user_id, limit)
        results = (await self.db.execute(query)).all()
        return [(user_id, num_mutual_friends) for user_id, num_mutual_friends in results]

    # Operations
    async def create_user(
        self,
        uid: str,
        username: str,
        first_name: str,
        last_name: str,
        phone_number: Optional[str] = None,
    ) -> Tuple[Optional[InternalUser], Optional[UserFieldErrors]]:
        """Create a new user with the given details."""
        new_user = UserRow(
            uid=uid,
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        try:
            # Initialize user preferences
            prefs = UserPrefsRow(user=new_user)  # type: ignore
            self.db.add(new_user)
            self.db.add(prefs)
            await self.db.commit()
            await self.db.refresh(new_user, ["id"])
            return (await self.get_user(new_user.id)), None
        except IntegrityError as e:
            await self.db.rollback()
            # A user with the same uid or username exists
            if await self.is_uid_taken(uid):
                error = UserFieldErrors(uid="User exists.")
                return None, error
            elif await self.is_username_taken(username):
                error = UserFieldErrors(username="Username taken.")
                return None, error
            else:
                # Unknown error
                print(e)
                return None, UserFieldErrors(other="Unknown error.")

    async def update_user(
        self,
        user_id: UserId,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        profile_picture_id: Optional[ImageId] = None,
    ) -> Tuple[Optional[InternalUser], Optional[UserFieldErrors]]:
        """Update the given user with the given details."""
        user = await UserQuery().user_id(user_id).execute_one(self.db)
        if user is None:
            return None, UserFieldErrors(uid="User not found")
        if profile_picture_id:
            image = await maybe_get_image_with_lock(self.db, user.id, profile_picture_id)
            if image is None:
                await self.db.rollback()
                return None, UserFieldErrors(other="Invalid image")
            image.used = True
            user.profile_picture_id = image.id
        if username:
            user.username = username
        if first_name:
            user.first_name = first_name
        if last_name:
            user.last_name = last_name
        try:
            await self.db.commit()
            return await self.get_user(user_id), None
        except IntegrityError as e:
            await self.db.rollback()
            if username and await self.is_username_taken(username):
                return None, UserFieldErrors(username="Username taken.")
            else:
                # Unknown error
                print(e)
                return None, UserFieldErrors(other="Unknown error.")

    async def soft_delete_user(self, user_id: UserId) -> None:
        """Mark the given user for deletion"""
        await self.db.execute(sa.update(UserRow).where(UserRow.id == user_id).values(deleted=True))
        await self.db.commit()

    async def hard_delete_user(self, user_id: UserId) -> None:
        """Mark the given user for deletion"""
        await self.db.execute(sa.delete(UserRow).where(UserRow.id == user_id))
        await self.db.commit()

    async def update_preferences(self, user_id: UserId, request: UserPrefs) -> UserPrefs:
        """Update the given user's preferences."""
        prefs: Optional[UserPrefsRow] = await UserPrefsQuery().user_id(user_id).execute_one(self.db)
        if prefs is None:
            # TODO(gmekkat): If this happens, we need to create the user's preferences row.
            return request
        prefs.follow_notifications = request.follow_notifications
        prefs.post_liked_notifications = request.post_liked_notifications
        if request.comment_notifications is not None:
            prefs.comment_notifications = request.comment_notifications
        if request.comment_liked_notifications is not None:
            prefs.comment_liked_notifications = request.comment_liked_notifications
        if request.searchable_by_phone_number is not None:
            prefs.searchable_by_phone_number = request.searchable_by_phone_number
        await self.db.commit()
        await self.db.refresh(prefs)
        return UserPrefs.from_orm(prefs)
