import uuid
from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import schemas
from stores import utils
from models import models


class CommentStore:
    def __init__(self, db: Session):
        self.db = db

    def get_like_count(self, comment_id: uuid.UUID) -> int:
        """Get the given comment's like count."""
        query = select(func.count()).select_from(models.CommentLike).where(models.CommentLike.comment_id == comment_id)
        return self.db.execute(query).scalar()

    def get_comments(
        self,
        caller_user_id: uuid.UUID,
        post_id: uuid.UUID,
        cursor: Optional[uuid.UUID],
        limit: int = 10
    ) -> schemas.comment.CommentPage:
        """Get up to the `limit` most recent comments made before `cursor`."""
        query = select(models.Comment, utils.is_comment_liked_query(caller_user_id)) \
            .options(*utils.eager_load_comment_options()) \
            .where(models.Comment.post_id == post_id, ~models.Comment.deleted)
        if cursor is not None:
            query = query.where(models.Comment.id < cursor)
        rows = self.db.execute(query.order_by(models.Comment.id.desc()).limit(limit)).all()
        comments = []
        for comment, liked in rows:
            orm_comment = schemas.comment.ORMComment.from_orm(comment)
            comments.append(schemas.comment.Comment(**orm_comment.dict(), liked=liked))
        next_cursor = None if len(comments) < limit else comments[-1].id
        return schemas.comment.CommentPage(comments=comments, cursor=next_cursor)

    def get_comment(self, comment_id: uuid.UUID) -> Optional[schemas.internal.InternalComment]:
        query = select(models.Comment) \
            .where(models.Comment.id == comment_id, ~models.Comment.deleted)
        comment = self.db.execute(query).scalars().first()
        if comment:
            return schemas.internal.InternalComment.from_orm(comment)
        return None

    def create_comment(self, user_id: uuid.UUID, post_id: uuid.UUID, content: str) -> schemas.internal.InternalComment:
        comment = models.Comment(user_id=user_id, post_id=post_id, content=content)
        self.db.add(comment)
        self.db.commit()
        return schemas.internal.InternalComment.from_orm(comment)

    def like_comment(self, comment_id: uuid.UUID, user_id: uuid.UUID):
        like = models.CommentLike(user_id=user_id, comment_id=comment_id)
        try:
            self.db.add(like)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            pass

    def unlike_comment(self, comment_id: uuid.UUID, user_id: uuid.UUID):
        query = delete(models.CommentLike).where(
            models.CommentLike.user_id == user_id, models.CommentLike.comment_id == comment_id)
        self.db.execute(query)
        self.db.commit()

    def delete_comment(self, comment_id: uuid.UUID):
        query = select(models.Comment).where(models.Comment.id == comment_id)
        comment = self.db.execute(query).scalars().first()
        if comment:
            comment.deleted = True
            self.db.commit()
        return
