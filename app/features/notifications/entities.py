from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import validator

from app.core.internal import InternalPost, InternalUser, InternalComment
from app.features.posts.entities import Post
from app.features.users.entities import PublicUser
from app.core.types import Base, UserId
from app.features.comments.entities import Comment


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
    post: Optional[Post]
    comment: Optional[Comment]

    @validator("created_at")
    def validate_created_at(cls, created_at):
        # Needed so Swift can automatically decode
        return created_at.replace(microsecond=0)


# Request types for background service
class PostLikeNotification(Base):
    post: InternalPost
    place_name: str
    liked_by: InternalUser


class PostSaveNotification(Base):
    post: InternalPost
    place_name: str
    saved_by: InternalUser


class CommentNotification(Base):
    post: InternalPost
    place_name: str
    comment: str
    comment_by: InternalUser


class CommentLikeNotification(Base):
    comment: InternalComment
    liked_by: InternalUser


class FollowNotification(Base):
    user_id: UserId
    followed_by: InternalUser
