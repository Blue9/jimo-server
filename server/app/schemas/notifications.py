from typing import Optional
from enum import Enum
from datetime import datetime

from pydantic import validator

from app.schemas.base import Base
from app.schemas.user import PublicUser
from app.schemas.post import Post


class ItemType(Enum):
    follow = "follow"
    like = "like"
    comment = "comment"


# TODO: Implement pagination
class PaginationToken(Base):
    follow_id: Optional[str]
    like_id: Optional[str]


class NotificationItem(Base):
    type: ItemType
    created_at: datetime
    user: PublicUser
    item_id: str
    post: Optional[Post]

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)
