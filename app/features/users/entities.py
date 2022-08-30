from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.types import Base, UserId, InternalBase, ImageId


class PublicUser(Base):
    id: UserId = Field(alias="userId")
    username: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str]
    post_count: int
    follower_count: int
    following_count: int


class UserPrefs(Base):
    follow_notifications: bool
    post_liked_notifications: bool
    # New fields, so they have to be optional
    comment_notifications: Optional[bool]
    comment_liked_notifications: Optional[bool]
    searchable_by_phone_number: Optional[bool]
    post_notifications: Optional[bool] = False


class UserFieldErrors(Base):
    uid: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    other: Optional[str]


class UserRelation(Enum):
    following = "following"
    blocked = "blocked"


NumMutualFriends = int
SuggestedUserIdItem = tuple[UserId, NumMutualFriends]


class InternalUser(InternalBase):
    id: UserId
    uid: str
    username: str
    username_lower: str
    first_name: str
    last_name: str
    phone_number: Optional[str]
    profile_picture_id: Optional[ImageId]
    profile_picture_url: Optional[str]
    profile_picture_blob_name: Optional[str]
    is_featured: bool
    is_admin: bool
    deleted: bool
    created_at: datetime
    updated_at: datetime
    post_count: int
    follower_count: int
    following_count: int
