"""
Response types for the admin API. Do not use anywhere other than admin API.
"""
from datetime import datetime
from typing import TypeVar, Generic
from uuid import UUID

from pydantic import Field, validator
from pydantic.generics import GenericModel

from app.core.types import Base, UserId, PostId
from app.features.places.entities import Place
from app.features.posts.entities import PostWithoutLikeSaveStatus
from app.features.users import validators
from app.features.users.types import CreateUserRequest


class AdminAPIUser(Base):
    id: UserId = Field(alias="userId")
    uid: str
    username: str
    first_name: str
    last_name: str
    phone_number: str | None = None
    profile_picture_url: str | None = None
    created_at: datetime
    is_featured: bool
    is_admin: bool
    deleted: bool


class AdminAPIPost(Base):
    id: PostId = Field(alias="postId")
    user: AdminAPIUser
    place: Place
    category: str
    custom_latitude: float | None
    custom_longitude: float | None
    content: str
    image_url: str | None
    stars: int | None
    deleted: bool
    created_at: datetime


class AdminAPIReport(Base):
    id: UUID
    post: PostWithoutLikeSaveStatus
    reported_by: AdminAPIUser
    details: str
    created_at: datetime


class AdminAPIFeedback(Base):
    id: UUID
    user: AdminAPIUser
    contents: str
    follow_up: bool
    created_at: datetime


T = TypeVar("T")


class AdminResponsePage(GenericModel, Generic[T]):
    total: int
    data: list[T]


# Request types
class AdminCreateUserRequest(CreateUserRequest):
    uid: str


class AdminUpdateUserRequest(Base):
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_featured: bool
    is_admin: bool
    deleted: bool

    _validate_username = validator("username", allow_reuse=True)(validators.validate_username)
    _validate_first_name = validator("first_name", allow_reuse=True)(validators.validate_name)
    _validate_last_name = validator("last_name", allow_reuse=True)(validators.validate_name)


class AdminUpdatePostRequest(Base):
    content: str | None = None
    deleted: bool

    @validator("content")
    def validate_content(cls, content):
        return content.strip()
