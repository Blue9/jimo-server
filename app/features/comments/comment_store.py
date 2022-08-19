from typing import Optional

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.helpers import eager_load_comment_options
from app.core.types import UserId, PostId, CommentId
from app.core.database.models import CommentRow, CommentLikeRow
from app.features.comments.entities import CommentWithoutLikeStatus, InternalComment


class CommentStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_like_count(self, comment_id: CommentId) -> int:
        """Get the given comment's like count."""
        query = sa.select(sa.func.count()).where(CommentLikeRow.comment_id == comment_id)
        result = await self.db.execute(query)
        like_count: int = result.scalar()  # type: ignore
        return like_count

    async def get_comments(
        self, post_id: PostId, after_comment_id: Optional[CommentId], limit: int = 10
    ) -> list[CommentWithoutLikeStatus]:
        """Get up to the `limit` most recent comments made after `after_comment_id`."""
        query = sa.select(CommentRow).options(*eager_load_comment_options()).where(CommentRow.post_id == post_id)
        if after_comment_id:
            query = query.where(CommentRow.id > after_comment_id)
        query = query.order_by(CommentRow.id.asc()).limit(limit)
        result = await self.db.execute(query)
        comments: list[CommentRow] = result.scalars().all()  # type: ignore
        return [CommentWithoutLikeStatus.from_orm(comment) for comment in comments]

    async def get_comment(self, comment_id: CommentId) -> Optional[InternalComment]:
        query = sa.select(CommentRow).where(CommentRow.id == comment_id)
        result = await self.db.execute(query)
        comment: Optional[CommentRow] = result.scalars().first()
        return InternalComment.from_orm(comment) if comment else None

    async def get_liked_comments(self, user_id: UserId, comment_ids: list[CommentId]) -> set[CommentId]:
        query = sa.select(CommentLikeRow.comment_id).where(
            CommentLikeRow.user_id == user_id, CommentLikeRow.comment_id.in_(comment_ids)
        )
        result = await self.db.execute(query)
        comment_ids: list[CommentId] = result.scalars().all()  # type: ignore
        return set(comment_ids)

    async def create_comment(self, user_id: UserId, post_id: PostId, content: str) -> InternalComment:
        comment = CommentRow(user_id=user_id, post_id=post_id, content=content)
        self.db.add(comment)
        await self.db.commit()
        await self.db.refresh(comment)
        return InternalComment.from_orm(comment)

    async def like_comment(self, comment_id: CommentId, user_id: UserId) -> None:
        like = CommentLikeRow(user_id=user_id, comment_id=comment_id)
        try:
            self.db.add(like)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            pass

    async def unlike_comment(self, comment_id: CommentId, user_id: UserId) -> None:
        query = sa.delete(CommentLikeRow).where(
            CommentLikeRow.user_id == user_id, CommentLikeRow.comment_id == comment_id
        )
        await self.db.execute(query)
        await self.db.commit()

    async def delete_comment(self, comment_id: CommentId):
        query = sa.delete(CommentRow).where(CommentRow.id == comment_id)
        await self.db.execute(query)
        await self.db.commit()
