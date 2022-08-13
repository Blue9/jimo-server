from typing import Optional

from pydantic import validator

from app.core.types import Base, PostId, CursorId
from app.features.comments.entities import CommentWithoutLikeStatus


class Comment(CommentWithoutLikeStatus):
    liked: bool


class CreateCommentRequest(Base):
    post_id: PostId
    content: str

    @validator("content")
    def validate_content(cls, content):
        content = content.strip()
        if len(content) == 0 or len(content) > 200:
            raise ValueError("Comments must be 1-200 characters")
        return content


class CommentPageResponse(Base):
    comments: list[Comment]
    cursor: Optional[CursorId]


class LikeCommentResponse(Base):
    likes: int
