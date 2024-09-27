"""
Response types for the admin API. Do not use anywhere other than admin API.
"""

from datetime import datetime
from typing import TypeVar, Generic
from uuid import UUID

from pydantic import Field, field_validator
from pydantic import BaseModel

from app.core.types import Base, UserId, PostId
from app.features.places.entities import Place
from app.features.posts.entities import PostWithoutLikeSaveStatus
from app.features.users.primitive_types import ValidatedName, ValidatedUsername
from app.features.users.types import CreateUserRequest


class AdminAPIUser(Base):
    id: UserId = Field(serialization_alias="userId", validation_alias="userId")
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
    id: PostId = Field(serialization_alias="postId", validation_alias="postId")
    user: AdminAPIUser
    place: Place
    category: str
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


class AdminResponsePage(BaseModel, Generic[T]):
    total: int
    data: list[T]


# Request types
class AdminCreateUserRequest(CreateUserRequest):
    uid: str


class AdminUpdateUserRequest(Base):
    username: ValidatedUsername | None = None
    first_name: ValidatedName | None = None
    last_name: ValidatedName | None = None
    is_featured: bool
    is_admin: bool
    deleted: bool


class AdminUpdatePostRequest(Base):
    content: str | None = None
    deleted: bool

    @field_validator("content")
    @classmethod
    def validate_content(cls, content: str):
        return content and content.strip()
