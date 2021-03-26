"""
Response types for the admin API. Do not use anywhere other than admin API.
"""
import uuid
from datetime import datetime
from typing import Optional, TypeVar, Generic

from pydantic import Field, validator
from pydantic.generics import GenericModel

from app import schemas
from app.schemas import validators
from app.schemas.base import Base, PhoneNumber
from app.schemas.place import Place
from app.schemas.post import ORMPost


# Base types
class User(Base):
    external_id: uuid.UUID = Field(alias="userId")
    uid: str
    username: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    profile_picture_url: Optional[str] = None
    created_at: datetime
    is_featured: bool
    is_admin: bool
    deleted: bool


class Post(Base):
    external_id: uuid.UUID = Field(alias="postId")
    user: User
    place: Place
    category: str
    custom_latitude: Optional[float]
    custom_longitude: Optional[float]
    content: str
    image_url: Optional[str]
    deleted: bool
    created_at: datetime


class Waitlist(Base):
    phone_number: str
    created_at: datetime


class Invite(Base):
    phone_number: str
    created_at: datetime


class Report(Base):
    id: int
    post: ORMPost
    reported_by: User
    details: str
    created_at: datetime


class Feedback(Base):
    id: int
    user: User
    contents: str
    follow_up: bool
    created_at: datetime


# Page
ModelType = TypeVar("ModelType")


class Page(GenericModel, Generic[ModelType]):
    total: int
    data: list[ModelType]


# Request types
class CreateUserRequest(schemas.user.CreateUserRequest):
    uid: str


class UpdateUserRequest(Base):
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_featured: bool
    is_admin: bool
    deleted: bool

    _validate_username = validator("username", allow_reuse=True)(validators.validate_username)
    _validate_first_name = validator("first_name", allow_reuse=True)(validators.validate_name)
    _validate_last_name = validator("last_name", allow_reuse=True)(validators.validate_name)


class UpdatePostRequest(Base):
    content: Optional[str] = None
    deleted: bool

    @validator("content")
    def validate_content(cls, content):
        return content.strip()


class CreateInviteRequest(Base):
    phone_number: PhoneNumber
