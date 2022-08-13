import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.models import CommentLikeRow
from app.core.types import CommentLikeId, CommentId, QueryEntity

CommentLikeQueryT = typing.TypeVar("CommentLikeQueryT", bound="CommentLikeQuery")


class CommentLikeQuery:
    def __init__(self, query_entity: QueryEntity):
        self.query: sa.sql.Select = sa.select(query_entity)

    def comment_id(self: CommentLikeQueryT, comment_id: CommentId) -> CommentLikeQueryT:
        self.query = self.query.where(CommentLikeRow.comment_id == comment_id)
        return self

    def cursor(self: CommentLikeQueryT, cursor_id: typing.Optional[CommentLikeId]) -> CommentLikeQueryT:
        if cursor_id:
            self.query = self.query.where(CommentLikeRow.id < cursor_id)
        return self

    # Limit and order
    def limit(self: CommentLikeQueryT, limit: int) -> CommentLikeQueryT:
        self.query = self.query.limit(limit)
        return self

    def order_by(self: CommentLikeQueryT, order_by) -> CommentLikeQueryT:
        self.query = self.query.order_by(order_by)
        return self

    async def execute_scalar(self: CommentLikeQueryT, session: AsyncSession) -> typing.Any:
        result = await session.execute(self.query)
        return result.scalar()
