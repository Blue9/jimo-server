import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import PostLikeRow, PostRow
from app.core.types import UserId, PostLikeId, PostId, QueryEntity

PostLikeQueryT = typing.TypeVar("PostLikeQueryT", bound="PostLikeQuery")


class PostLikeQuery:
    def __init__(self, query_entity: QueryEntity = PostLikeRow):
        self.query: sa.sql.Select = sa.select(query_entity)
        self.query_entity = query_entity

    def post_id(self: PostLikeQueryT, post_id: PostId) -> PostLikeQueryT:
        self.query = self.query.where(PostLikeRow.post_id == post_id)
        return self

    def liked_by(self: PostLikeQueryT, user_id: UserId) -> PostLikeQueryT:
        self.query = self.query.where(PostLikeRow.user_id == user_id)
        return self

    def not_liked_by(self: PostLikeQueryT, user_id: UserId) -> PostLikeQueryT:
        self.query = self.query.where(PostLikeRow.user_id != user_id)
        return self

    def post_author(self: PostLikeQueryT, user_id: UserId) -> PostLikeQueryT:
        self.query = self.query.join(PostRow).where(PostRow.user_id == user_id, ~PostRow.deleted)
        return self

    # Cursor id
    def cursor(self: PostLikeQueryT, cursor_id: typing.Optional[PostLikeId]) -> PostLikeQueryT:
        if cursor_id:
            self.query = self.query.where(PostLikeRow.id < cursor_id)
        return self

    # Limit and order
    def limit(self: PostLikeQueryT, limit: int) -> PostLikeQueryT:
        self.query = self.query.limit(limit)
        return self

    def order_by(self: PostLikeQueryT, order_by) -> PostLikeQueryT:
        self.query = self.query.order_by(order_by)
        return self

    async def execute_exists(self: PostLikeQueryT, session: AsyncSession) -> bool:
        result = await session.execute(self.query.exists().select())
        exists: bool = result.scalar()  # type: ignore
        return exists

    async def execute_many(self: PostLikeQueryT, session: AsyncSession) -> list[QueryEntity]:
        result = await session.execute(self.query)
        return result.scalars().all()

    async def execute_scalar(self: PostLikeQueryT, session: AsyncSession) -> typing.Any:
        result = await session.execute(self.query)
        return result.scalar()
