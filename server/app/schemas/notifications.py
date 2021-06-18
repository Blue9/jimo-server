import uuid
from typing import Optional
from enum import Enum
from datetime import datetime

from pydantic import validator

from app.schemas.base import Base
from app.schemas.comment import Comment
from app.schemas.user import PublicUser
from app.schemas.post import Post


class ItemType(Enum):
    follow = "follow"
    like = "like"
    comment = "comment"


class NotificationItem(Base):
    type: ItemType
    created_at: datetime
    user: PublicUser
    item_id: uuid.UUID
    post: Optional[Post]
    comment: Optional[Comment]

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)


class NotificationFeedResponse(Base):
    notifications: list[NotificationItem]
    cursor: Optional[uuid.UUID]
