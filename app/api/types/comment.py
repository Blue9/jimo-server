from typing import Optional

from pydantic import validator
from shared.api.base import Base
from shared.api.comment import Comment
from shared.api.type_aliases import PostId, CursorId


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
