import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import UserRelationRow, UserRelationType
from app.core.types import UserId, UserRelationId, QueryEntity

UserRelationQueryT = typing.TypeVar("UserRelationQueryT", bound="UserRelationQuery")


class UserRelationQuery:
    def __init__(
        self,
        relation: typing.Optional[UserRelationType] = None,
        query_entity: QueryEntity = UserRelationRow,
    ):
        self.query: sa.sql.Select = sa.select(query_entity)
        self.query_entity = query_entity
        if relation is not None:
            self.query = self.query.where(UserRelationRow.relation == relation)

    def from_user_id(self: UserRelationQueryT, user_id: UserId) -> UserRelationQueryT:
        self.query = self.query.where(UserRelationRow.from_user_id == user_id)
        return self

    def to_user_id(self: UserRelationQueryT, user_id: UserId) -> UserRelationQueryT:
        self.query = self.query.where(UserRelationRow.to_user_id == user_id)
        return self

    def to_user_id_in(self: UserRelationQueryT, user_ids: list[UserId]) -> UserRelationQueryT:
        self.query = self.query.where(UserRelationRow.to_user_id.in_(user_ids))
        return self

    def cursor(self: UserRelationQueryT, cursor_id: typing.Optional[UserRelationId]) -> UserRelationQueryT:
        if cursor_id:
            self.query = self.query.where(UserRelationRow.id < cursor_id)
        return self

    # Limit and order
    def limit(self: UserRelationQueryT, limit: int) -> UserRelationQueryT:
        self.query = self.query.limit(limit)
        return self

    def order_by(self: UserRelationQueryT, order_by) -> UserRelationQueryT:
        self.query = self.query.order_by(order_by)
        return self

    async def execute_exists(self: UserRelationQueryT, session: AsyncSession) -> bool:
        result = await session.execute(self.query.exists().select())
        exists: bool = result.scalar()  # type: ignore
        return exists

    async def execute_many(self: UserRelationQueryT, session: AsyncSession) -> list[QueryEntity]:
        # Filters out deleted users
        result = await session.execute(self.query)
        return result.scalars().all()

    async def execute_one(self: UserRelationQueryT, session: AsyncSession) -> typing.Optional[QueryEntity]:
        result = await session.execute(self.query)
        return result.scalars().first()
