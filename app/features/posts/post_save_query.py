import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import PostRow, PostSaveRow
from app.core.types import UserId, PostSaveId, PostId, QueryEntity

PostSaveQueryT = typing.TypeVar("PostSaveQueryT", bound="PostSaveQuery")


# TODO(gautam): this class is basically the same as PostLikeQuery, could be consolidated
class PostSaveQuery:
    def __init__(self, query_entity: QueryEntity = PostSaveRow):
        self.query: sa.sql.Select = sa.select(query_entity)
        self.query_entity = query_entity

    def post_id(self: PostSaveQueryT, post_id: PostId) -> PostSaveQueryT:
        self.query = self.query.where(PostSaveRow.post_id == post_id)
        return self

    def cursor(self: PostSaveQueryT, cursor_id: typing.Optional[PostSaveId]) -> PostSaveQueryT:
        if cursor_id:
            self.query = self.query.where(PostSaveRow.id < cursor_id)
        return self

    def saved_by(self: PostSaveQueryT, user_id: UserId) -> PostSaveQueryT:
        self.query = self.query.where(PostSaveRow.user_id == user_id)
        return self

    def not_saved_by(self: PostSaveQueryT, user_id: UserId) -> PostSaveQueryT:
        self.query = self.query.where(PostSaveRow.user_id != user_id)
        return self

    def post_author(self: PostSaveQueryT, user_id: UserId) -> PostSaveQueryT:
        self.query = self.query.join(PostRow).where(PostRow.user_id == user_id, ~PostRow.deleted)
        return self

    # Limit and order
    def limit(self: PostSaveQueryT, limit: int) -> PostSaveQueryT:
        self.query = self.query.limit(limit)
        return self

    def order_by(self: PostSaveQueryT, order_by) -> PostSaveQueryT:
        self.query = self.query.order_by(order_by)
        return self

    async def execute_exists(self: PostSaveQueryT, session: AsyncSession) -> bool:
        result = await session.execute(self.query.exists().select())
        exists: bool = result.scalar()  # type: ignore
        return exists

    async def execute_many(self: PostSaveQueryT, session: AsyncSession) -> list[PostSaveRow]:
        result = await session.execute(self.query)
        return result.scalars().all()
