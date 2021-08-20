import datetime
import uuid
from typing import Optional

from pydantic import Field, validator

from schemas.base import Base
from schemas.user import PublicUser


class ORMComment(Base):
    id: uuid.UUID = Field(alias="commentId")
    user: PublicUser
    post_id: uuid.UUID
    content: str
    created_at: datetime.datetime
    like_count: int

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)


class Comment(ORMComment):
    liked: bool


# Request

class CreateCommentRequest(Base):
    post_id: uuid.UUID
    content: str

    @validator("content")
    def validate_content(cls, content):
        content = content.strip()
        if len(content) == 0 or len(content) > 200:
            raise ValueError("Comments must be 1-200 characters")
        return content


# Response

class CommentPage(Base):
    comments: list[Comment]
    cursor: Optional[uuid.UUID]


class LikeCommentResponse(Base):
    likes: int
