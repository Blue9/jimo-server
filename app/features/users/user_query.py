import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import concat

from app.core.database.helpers import eager_load_user_options
from app.core.database.models import UserRow, UserPrefsRow
from app.core.types import UserId, QueryEntity

UserQueryT = typing.TypeVar("UserQueryT", bound="UserQuery")


class UserQuery:
    def __init__(self: UserQueryT, query_entity: QueryEntity = UserRow):
        """You can set query_entity to UserRow.id if you only want to query user IDs."""
        self.query: sa.sql.Select = sa.select(query_entity)
        self.query_entity = query_entity

    # Simple fields
    def user_id(self: UserQueryT, user_id: UserId) -> UserQueryT:
        self.query = self.query.where(UserRow.id == user_id)
        return self

    def username(self: UserQueryT, username: str) -> UserQueryT:
        self.query = self.query.where(UserRow.username_lower == username.lower())
        return self

    def uid(self: UserQueryT, uid: str) -> UserQueryT:
        self.query = self.query.where(UserRow.uid == uid)
        return self

    def is_featured(self: UserQueryT) -> UserQueryT:
        self.query = self.query.where(UserRow.is_featured)
        return self

    # Complex query
    def filter_by_keyword(self: UserQueryT, query: str) -> UserQueryT:
        # TODO this is inefficient, we should move to a real search engine
        query = query.replace("\\", "\\\\").replace("_", "\\_").replace("%", "\\%")
        ilike_query = f"{query}%"
        self.query = self.query.where(
            UserRow.username_lower.ilike(ilike_query)
            | concat(UserRow.first_name, " ", UserRow.last_name).ilike(ilike_query)
        )
        return self

    # Collection query
    def user_id_in(self: UserQueryT, user_ids: list[UserId]) -> UserQueryT:
        self.query = self.query.where(UserRow.id.in_(user_ids))
        return self

    def phone_number_in(self: UserQueryT, phone_numbers: typing.Sequence[str]) -> UserQueryT:
        self.query = self.query.where(UserRow.phone_number.in_(phone_numbers))
        return self

    # Joining query
    def is_searchable_by_phone_number(self: UserQueryT) -> UserQueryT:
        self.query = self.query.join(UserPrefsRow).where(UserPrefsRow.searchable_by_phone_number)
        return self

    # Limit and order
    def limit(self: UserQueryT, limit: int) -> UserQueryT:
        self.query = self.query.limit(limit)
        return self

    def order_by(self: UserQueryT, order_by) -> UserQueryT:
        self.query = self.query.order_by(order_by)
        return self

    # Execution
    async def execute_many(self: UserQueryT, session: AsyncSession, include_deleted: bool = False) -> list[QueryEntity]:
        result = await self._execute(session, include_deleted=include_deleted)
        return result.all()

    async def execute_one(self: UserQueryT, session: AsyncSession, include_deleted: bool = False) -> QueryEntity:
        result = await self._execute(session, include_deleted=include_deleted)
        return result.first()

    async def execute_exists(self: UserQueryT, session: AsyncSession, include_deleted: bool = True) -> bool:
        if not include_deleted:
            query = self.query.where(~UserRow.deleted)
        else:
            query = self.query
        result = await session.execute(query.exists().select())
        exists: bool = result.scalar()  # type: ignore
        return exists

    async def _execute(self: UserQueryT, session: AsyncSession, include_deleted: bool):
        query = self.query
        if self.query_entity is UserRow:
            query = query.options(*eager_load_user_options())
        if not include_deleted:
            query = query.where(~UserRow.deleted)
        result = await session.execute(query)
        return result.scalars()
