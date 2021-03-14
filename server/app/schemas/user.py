import uuid
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

    @validator("username")
    def validate_username(cls, username: str):
        username = username.strip()
        if not validators.is_valid_username(username):
            raise ValueError("Username must be 3-20 characters and alphanumeric")
        return username

    @validator("first_name")
    def validate_first_name(cls, first_name: str):
        first_name = first_name.strip()
        if not validators.is_valid_name(first_name):
            raise ValueError("First name must be 1-100 characters")
        return first_name

    @validator("last_name")
    def validate_last_name(cls, last_name: str):
        last_name = last_name.strip()
        if not validators.is_valid_name(last_name):
            raise ValueError("Last name must be 1-100 characters")
        return last_name


class UpdateProfileRequest(Base):
    profile_picture_id: Optional[uuid.UUID]
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]

    @validator("username")
    def validate_username(cls, username):
        if username is None:
            return
        return CreateUserRequest.validate_username(username)

    @validator("first_name")
    def validate_first_name(cls, first_name):
        if first_name is None:
            return
        return CreateUserRequest.validate_first_name(first_name)

    @validator("last_name")
    def validate_last_name(cls, last_name):
        if last_name is None:
            return
        return CreateUserRequest.validate_last_name(last_name)


class PhoneNumberList(Base):
    phone_numbers: list[PhoneNumber]


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
    followed: bool
    followers: Optional[int]


class NotificationTokenRequest(Base):
    token: str
