from typing import Optional, Sequence

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.helpers import eager_load_user_options
from app.features.images.image_utils import maybe_get_image
from app.core.database.models import (
    UserRow,
    UserPrefsRow,
    UserRelationRow,
    UserRelationType,
)
from app.core.types import PhoneNumber, UserId, ImageId
from app.features.users.entities import (
    UserPrefs,
    SuggestedUserIdItem,
    UserFieldErrors,
    InternalUser,
)


class UserStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def user_exists(self, username: Optional[str] = None, uid: Optional[str] = None) -> bool:
        """Return whether or not a user (deleted or not) with the given attributes exists."""
        query = sa.select(UserRow.id)
        if username:
            query = query.where(UserRow.username_lower == username.lower())
        if uid:
            query = query.where(UserRow.uid == uid)
        result = await self.db.execute(query.exists().select())
        user_exists: bool = result.scalar()  # type: ignore
        return user_exists

    async def get_user(
        self,
        user_id: Optional[UserId] = None,
        uid: Optional[str] = None,
        username: Optional[str] = None,
    ) -> Optional[InternalUser]:
        query = sa.select(UserRow).options(*eager_load_user_options()).where(~UserRow.deleted)
        if user_id:
            query = query.where(UserRow.id == user_id)
        if uid:
            query = query.where(UserRow.uid == uid)
        if username:
            query = query.where(UserRow.username_lower == username.lower())
        result = await self.db.execute(query)
        user: Optional[UserRow] = result.scalars().first()
        return InternalUser.model_validate(user) if user else None

    async def get_users(self, user_ids: list[UserId]) -> dict[UserId, InternalUser]:
        query = sa.select(UserRow).options(*eager_load_user_options()).where(UserRow.id.in_(user_ids), ~UserRow.deleted)
        result = await self.db.execute(query)
        users = result.scalars().all()
        return {user.id: InternalUser.model_validate(user) for user in users}

    async def get_users_by_phone_number(self, phone_numbers: Sequence[PhoneNumber], limit: int = 100) -> list[UserId]:
        """Return up to `limit` users with the given phone numbers."""
        query = (
            sa.select(UserRow.id)
            .join(UserPrefsRow)
            .where(
                UserRow.phone_number.in_(phone_numbers),
                UserPrefsRow.searchable_by_phone_number,
            )
            .limit(limit)
        )
        result = await self.db.execute(query)
        user_ids = result.scalars().all()
        return user_ids  # type: ignore

    async def get_user_preferences(self, user_id: UserId) -> UserPrefs:
        query = sa.select(UserPrefsRow).where(UserPrefsRow.user_id == user_id)
        result = await self.db.execute(query)
        prefs = result.scalars().first()
        return (
            UserPrefs.model_validate(prefs)
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
        query = sa.select(UserRow.id).where(UserRow.is_featured)
        result = await self.db.execute(query)
        return result.scalars().all()  # type: ignore

    async def get_suggested_users(self, user_id: UserId, limit: int = 25) -> list[SuggestedUserIdItem]:
        """Get the list of suggested users for the given user_id."""
        query = self._get_suggested_users_query(user_id, limit)
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
    ) -> tuple[Optional[InternalUser], Optional[UserFieldErrors]]:
        """Create a new user with the given details."""
        new_user = UserRow(
            uid=uid,
            username=username,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
        )
        prefs = UserPrefsRow(user=new_user)
        try:
            self.db.add(new_user)
            self.db.add(prefs)
            await self.db.commit()
            await self.db.refresh(new_user, ["id"])
            return (await self.get_user(user_id=new_user.id)), None
        except IntegrityError as e:
            await self.db.rollback()
            # A user with the same uid or username exists
            if await self.user_exists(uid=uid):
                error = UserFieldErrors(uid="User exists.")
                return None, error
            elif await self.user_exists(username=username):
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
    ) -> tuple[InternalUser | None, UserFieldErrors | None]:
        """Update the given user with the given details."""
        query = sa.select(UserRow).where(UserRow.id == user_id)
        result = await self.db.execute(query)
        user = result.scalars().first()
        if user is None:
            return None, UserFieldErrors(uid="User not found")
        if profile_picture_id:
            image = await maybe_get_image(self.db, user.id, profile_picture_id)
            if image is None:
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
            return await self.get_user(user_id=user_id), None
        except IntegrityError as e:
            await self.db.rollback()
            if username and await self.user_exists(username=username):
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
        query = sa.select(UserPrefsRow).where(UserPrefsRow.user_id == user_id)
        result = await self.db.execute(query)
        prefs: Optional[UserPrefsRow] = result.scalars().first()
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
        if request.post_notifications is not None:
            prefs.post_notifications = request.post_notifications
        await self.db.commit()
        await self.db.refresh(prefs)
        return UserPrefs.model_validate(prefs)

    def _get_suggested_users_query(self, user_id: UserId, limit: int) -> sa.sql.Select:
        """
        How this is computed:
        We first get the list of followers for user_id. We then retrieve the list of users that the followers follow,
        minus the users the given user is already following. This list is then sorted by the # of "mutual followers."
        """
        cte = (
            sa.select(UserRelationRow.to_user_id.label("id"))
            .select_from(UserRelationRow)
            .where(
                UserRelationRow.from_user_id == user_id,
                UserRelationRow.relation == UserRelationType.following,
            )
            .cte("already_followed")
        )
        return (
            sa.select(UserRelationRow.to_user_id, sa.func.count(UserRelationRow.to_user_id))
            .select_from(UserRelationRow)
            .join(cte, cte.c.id == UserRelationRow.from_user_id)
            .where(UserRelationRow.to_user_id.not_in(sa.select(cte.c.id)))
            .where(UserRelationRow.to_user_id != user_id)
            .group_by(UserRelationRow.to_user_id)
            .order_by(sa.func.count(UserRelationRow.to_user_id).desc())
            .limit(limit)
        )
