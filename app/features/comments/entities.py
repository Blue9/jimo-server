import datetime

from pydantic import Field, validator

from app.features.users.entities import PublicUser
from app.core.types import Base, PostId, CommentId


class CommentWithoutLikeStatus(Base):
    id: CommentId = Field(alias="commentId")
    user: PublicUser
    post_id: PostId
    content: str
    created_at: datetime.datetime
    like_count: int

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)


class Comment(CommentWithoutLikeStatus):
    liked: bool