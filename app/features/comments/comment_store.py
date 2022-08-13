from typing import Optional, Tuple

from sqlalchemy import func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.internal import InternalComment
from app.core.types import UserId, PostId, CommentId, CursorId
from app.core.database.models import CommentRow, CommentLikeRow
from app.features.comments.entities import CommentWithoutLikeStatus
from app.features.comments.comment_query import CommentQuery


class CommentStore:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_like_count(self, comment_id: CommentId) -> int:
        """Get the given comment's like count."""
        return await CommentLikeQuery(func.count()).comment_id(comment_id).execute_scalar(self.db)  # type: ignore

    async def get_comments(
        self, post_id: PostId, cursor: Optional[CursorId], limit: int = 10
    ) -> Tuple[list[CommentWithoutLikeStatus], Optional[CursorId]]:
        """Get up to the `limit` most recent comments made before `cursor`."""
        comments = (
            await CommentQuery()
            .post_id(post_id)
            .cursor(cursor)
            .order_by(CommentRow.id.asc())
            .limit(limit)
            .execute_many(self.db, eager_load=True)
        )
        next_cursor = None if len(comments) < limit else comments[-1].id
        return [CommentWithoutLikeStatus.from_orm(comment) for comment in comments], next_cursor

    async def get_comment(self, comment_id: CommentId) -> Optional[InternalComment]:
        comment = await CommentQuery().comment_id(comment_id).execute_one(self.db)
        return InternalComment.from_orm(comment) if comment else None

    async def get_liked_comments(self, user_id: UserId, comment_ids: list[CommentId]) -> set[CommentId]:
        comment_ids = (
            await CommentQuery(CommentRow.id).comment_id_in(comment_ids).liked_by_user(user_id).execute_many(self.db)
        )
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
        query = delete(CommentLikeRow).where(CommentLikeRow.user_id == user_id, CommentLikeRow.comment_id == comment_id)
        await self.db.execute(query)
        await self.db.commit()

    async def delete_comment(self, comment_id: CommentId):
        comment: Optional[CommentRow] = await CommentQuery().comment_id(comment_id).execute_one(self.db)
        if comment:
            comment.deleted = True
            await self.db.commit()
        return
