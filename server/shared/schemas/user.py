import uuid
from enum import Enum
from typing import Optional

from pydantic import Field, validator

from shared.schemas import validators
from shared.schemas.base import Base, PhoneNumber


# ORM types
class PublicUser(Base):
    id: uuid.UUID = Field(alias="userId")
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


# Request types
class CreateUserRequest(Base):
    username: str
    first_name: str
    last_name: str

    _validate_username = validator("username", allow_reuse=True)(validators.validate_username)
    _validate_first_name = validator("first_name", allow_reuse=True)(validators.validate_name)
    _validate_last_name = validator("last_name", allow_reuse=True)(validators.validate_name)


class UpdateProfileRequest(Base):
    profile_picture_id: Optional[uuid.UUID] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    _validate_username = validator("username", allow_reuse=True)(validators.validate_username)
    _validate_first_name = validator("first_name", allow_reuse=True)(validators.validate_name)
    _validate_last_name = validator("last_name", allow_reuse=True)(validators.validate_name)


class PhoneNumberList(Base):
    phone_numbers: list[PhoneNumber]

    @validator("phone_numbers")
    def validate_phone_number(cls, phone_numbers):
        if len(phone_numbers) > 5000:
            raise ValueError("Phone number list too long, max length is 5000")
        return phone_numbers


class UsernameList(Base):
    usernames: list[str]

    @validator("usernames")
    def validate_usernames(cls, usernames):
        if len(usernames) > 100:
            raise ValueError("Username list too long, max length is 100")
        return usernames


# Response types
class UserFieldErrors(Base):
    uid: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    other: Optional[str]


class CreateUserResponse(Base):
    created: Optional[PublicUser]
    error: Optional[UserFieldErrors]


class UpdateProfileResponse(Base):
    user: Optional[PublicUser]
    error: Optional[UserFieldErrors]


class FollowUserResponse(Base):
    followed: bool  # legacy, used for backwards compatibility
    followers: Optional[int]


class UserRelation(Enum):
    following = "following"
    blocked = "blocked"


class RelationToUser(Base):
    relation: Optional[UserRelation]


class FollowFeedItem(Base):
    user: PublicUser
    relation: Optional[UserRelation]


class FollowFeedResponse(Base):
    users: list[FollowFeedItem]
    cursor: Optional[uuid.UUID]


class NotificationTokenRequest(Base):
    token: str

    @validator("token")
    def validate_token(cls, token):
        if len(token) == 0:
            raise ValueError("Invalid token")
        return token
