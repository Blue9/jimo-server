from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import field_validator

from app.core.types import Base, CursorId
from app.features.comments.types import Comment
from app.features.posts.entities import Post
from app.features.users.entities import PublicUser


class NotificationTokenRequest(Base):
    token: str

    @field_validator("token")
    @classmethod
    def validate_token(cls, token):
        if len(token) == 0:
            raise ValueError("Invalid token")
        return token


class ItemType(Enum):
    follow = "follow"
    like = "like"
    comment = "comment"
    save = "save"


class NotificationItem(Base):
    type: ItemType
    created_at: datetime
    user: PublicUser
    item_id: UUID
    post: Post | None = None
    comment: Comment | None = None

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)


class NotificationFeedResponse(Base):
    notifications: list[NotificationItem]
    cursor: CursorId | None = None
