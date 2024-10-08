from datetime import datetime
from typing import Literal

from pydantic import Field

from app.core.types import Base, InternalBase, UserId, ImageId


class PublicUser(Base):
    # The double alias rather than just alias is to appease VS Code
    id: UserId = Field(serialization_alias="userId", validation_alias="userId")
    username: str
    first_name: str
    last_name: str
    profile_picture_url: str | None
    post_count: int
    follower_count: int
    following_count: int


class UserPrefs(Base):
    follow_notifications: bool
    post_liked_notifications: bool
    # New fields, so they have to be optional
    comment_notifications: bool | None = None
    comment_liked_notifications: bool | None = None
    searchable_by_phone_number: bool | None = None
    post_notifications: bool | None = None


class UserFieldErrors(Base):
    uid: str | None = None
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    other: str | None = None


UserRelation = Literal["following", "blocked"]


NumMutualFriends = int
SuggestedUserIdItem = tuple[UserId, NumMutualFriends]


class InternalUser(InternalBase):
    id: UserId
    uid: str
    username: str
    username_lower: str
    first_name: str
    last_name: str
    phone_number: str | None
    profile_picture_id: ImageId | None
    profile_picture_url: str | None
    profile_picture_blob_name: str | None
    is_featured: bool
    is_admin: bool
    deleted: bool
    created_at: datetime
    updated_at: datetime
    post_count: int
    follower_count: int
    following_count: int

    def to_public(self):
        return PublicUser(
            id=self.id,
            username=self.username,
            first_name=self.first_name,
            last_name=self.last_name,
            profile_picture_url=self.profile_picture_url,
            post_count=self.post_count,
            follower_count=self.follower_count,
            following_count=self.following_count,
        )
