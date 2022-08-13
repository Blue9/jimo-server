from enum import Enum
from typing import Optional

from pydantic import Field

from app.core.types import Base, UserId


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
    post_notifications: Optional[bool] = False  # Here for backwards-compatibility, remove later
    follow_notifications: bool
    post_liked_notifications: bool
    # New fields, so they have to be optional
    comment_notifications: Optional[bool]
    comment_liked_notifications: Optional[bool]
    searchable_by_phone_number: Optional[bool]


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