import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.helpers import eager_load_post_options
from app.core.database.models import PostRow, PostLikeRow, PostSaveRow
from app.core.types import UserId, PostId, PlaceId, QueryEntity

PostQueryT = typing.TypeVar("PostQueryT", bound="PostQuery")


class PostQuery:
    def __init__(self: PostQueryT, query_entity: QueryEntity = PostRow):
        self.query: sa.sql.Select = sa.select(query_entity)
        self.query_entity = query_entity

    def user_id(self: PostQueryT, user_id: UserId) -> PostQueryT:
        self.query = self.query.where(PostRow.user_id == user_id)
        return self

    def place_id(self: PostQueryT, place_id: PlaceId) -> PostQueryT:
        self.query = self.query.where(PostRow.place_id == place_id)
        return self

    def post_id(self: PostQueryT, post_id: PostId) -> PostQueryT:
        self.query = self.query.where(PostRow.id == post_id)
        return self

    def post_id_in(self: PostQueryT, post_ids: list[PostId]) -> PostQueryT:
        self.query = self.query.where(PostRow.id.in_(post_ids))
        return self

    def cursor(self: PostQueryT, cursor_id: typing.Optional[PostId]) -> PostQueryT:
        if cursor_id:
            self.query = self.query.where(PostRow.id < cursor_id)
        return self

    # Join queries
    def liked_by_user(self: PostQueryT, user_id: UserId) -> PostQueryT:
        self.query = self.query.join(PostLikeRow).where(PostLikeRow.user_id == user_id)
        return self

    def saved_by_user(self: PostQueryT, user_id: UserId) -> PostQueryT:
        self.query = self.query.join(PostSaveRow).where(PostSaveRow.user_id == user_id)
        return self

    # Limit and order
    def limit(self: PostQueryT, limit: int) -> PostQueryT:
        self.query = self.query.limit(limit)
        return self

    def order_by(self: PostQueryT, order_by) -> PostQueryT:
        self.query = self.query.order_by(order_by)
        return self

    # Execution
    async def execute_many(self: PostQueryT, session: AsyncSession, include_deleted=False) -> list[QueryEntity]:
        result = await self._execute(session, include_deleted=include_deleted)
        return result.all()

    async def execute_one(
        self: PostQueryT, session: AsyncSession, include_deleted=False
    ) -> typing.Optional[QueryEntity]:
        result = await self._execute(session, include_deleted=include_deleted)
        return result.first()

    async def execute_exists(self: PostQueryT, session: AsyncSession, include_deleted=True) -> bool:
        query = self.query
        if not include_deleted:
            query = query.where(~PostRow.deleted)
        result = await session.execute(query.exists().select())
        exists: bool = result.scalar()  # type: ignore
        return exists

    async def _execute(self: PostQueryT, session: AsyncSession, include_deleted=False):
        query = self.query
        if self.query_entity is PostRow:
            query = query.options(*eager_load_post_options())
        if not include_deleted:
            query = query.where(~PostRow.deleted)
        result = await session.execute(query)
        return result.scalars()
