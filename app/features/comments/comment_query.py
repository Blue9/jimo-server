import typing

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.types import UserId, PostId, CommentId, QueryEntity
from app.core.database.models import CommentRow, CommentLikeRow, PostRow
from app.core.database.helpers import eager_load_comment_options

CommentQueryT = typing.TypeVar("CommentQueryT", bound="CommentQuery")


class CommentQuery:
    def __init__(self, query_entity: QueryEntity = CommentRow):
        self.query: sa.sql.Select = sa.select(query_entity)
        self.query_entity = query_entity

    def post_id(self: CommentQueryT, post_id: PostId) -> CommentQueryT:
        self.query = self.query.where(CommentRow.post_id == post_id)
        return self

    def not_user_id(self: CommentQueryT, user_id: UserId) -> CommentQueryT:
        self.query = self.query.where(CommentRow.user_id != user_id)
        return self

    def post_author(self: CommentQueryT, user_id: UserId) -> CommentQueryT:
        self.query = self.query.join(PostRow).where(PostRow.user_id == user_id)
        return self

    def comment_id(self: CommentQueryT, comment_id: CommentId) -> CommentQueryT:
        self.query = self.query.where(CommentRow.id == comment_id)
        return self

    def comment_id_in(self: CommentQueryT, comment_ids: typing.Sequence[CommentId]) -> CommentQueryT:
        self.query = self.query.where(CommentRow.id.in_(comment_ids))
        return self

    def cursor(self: CommentQueryT, cursor_id: typing.Optional[CommentId]) -> CommentQueryT:
        if cursor_id:
            self.query = self.query.where(CommentRow.id < cursor_id)
        return self

    # Join queries
    def liked_by_user(self: CommentQueryT, user_id: UserId) -> CommentQueryT:
        self.query = self.query.join(CommentLikeRow).where(CommentLikeRow.user_id == user_id)
        return self

    # Limit and order
    def limit(self: CommentQueryT, limit: int) -> CommentQueryT:
        self.query = self.query.limit(limit)
        return self

    def order_by(self: CommentQueryT, order_by) -> CommentQueryT:
        self.query = self.query.order_by(order_by)
        return self

    async def execute_many(self: CommentQueryT, session: AsyncSession, eager_load: bool = False) -> list[QueryEntity]:
        result = await self._execute(session, eager_load=eager_load)
        return result.all()

    async def execute_one(
        self: CommentQueryT, session: AsyncSession, eager_load: bool = False
    ) -> typing.Optional[QueryEntity]:
        result = await self._execute(session, eager_load=eager_load)
        return result.first()

    async def _execute(self: CommentQueryT, session: AsyncSession, eager_load: bool = False):
        query = self.query.where(~CommentRow.deleted)
        if eager_load:
            query = query.options(*eager_load_comment_options())
        result = await session.execute(query)
        return result.scalars()
