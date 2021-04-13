import uuid
from enum import Enum
from typing import Optional

from pydantic import Field, validator

from app.schemas import validators
from app.schemas.base import Base, PhoneNumber


# ORM types
class PublicUser(Base):
    external_id: uuid.UUID = Field(alias="userId")
    username: str
    first_name: str
    last_name: str
    profile_picture_url: Optional[str]
    post_count: int
    follower_count: int
    following_count: int


class UserPrefs(Base):
    post_notifications: bool
    follow_notifications: bool
    post_liked_notifications: bool


class PrivateUser(PublicUser):
    uid: str
    preferences: Optional[UserPrefs]


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
        if len(usernames) > 1000:
            raise ValueError("Username list too long, max length is 1000")
        return usernames


# Response types
class UserFieldErrors(Base):
    uid: Optional[str]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    other: Optional[str]


class CreateUserResponse(Base):
    created: Optional[PrivateUser]
    error: Optional[UserFieldErrors]


class UpdateProfileResponse(Base):
    user: Optional[PrivateUser]
    error: Optional[UserFieldErrors]


class FollowUserResponse(Base):
    followed: bool  # legacy, used for backwards compatibility
    followers: Optional[int]


class UserRelation(Enum):
    following = "following"
    blocked = "blocked"


class RelationToUser(Base):
    relation: Optional[UserRelation]


class NotificationTokenRequest(Base):
    token: str
