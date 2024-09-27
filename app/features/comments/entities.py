from datetime import datetime

from pydantic import Field, field_validator

from app.features.users.entities import PublicUser
from app.core.types import Base, PostId, CommentId, InternalBase, UserId


class CommentWithoutLikeStatus(Base):
    id: CommentId = Field(serialization_alias="commentId", validation_alias="commentId")
    user: PublicUser
    post_id: PostId
    content: str
    created_at: datetime
    like_count: int

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, created_at: datetime):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)


class InternalComment(InternalBase):
    id: CommentId
    user_id: UserId
    post_id: PostId
    content: str
    deleted: bool
    created_at: datetime
